from typing import Optional, Tuple
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from .types import SearchTool, SearchResult
from .utils import format_results_full
import logging
import re
import json

logger = logging.getLogger(__name__)

RETRIEVAL_PROMPT = """
You will be given a query by a human user. Your job is solely to gather information from an external knowledge base that would help the user answer the query. To gather this information, you have been equipped with a search engine tool that you can use to query the external knowledge base. Here is a description of the search engine tool: <tool_description>{description}</tool_description>

You can make a call to the search engine tool by inserting a query within <search_query> tags like so: <search_query>query</search_query>. You'll then get results back within <search_result></search_result> tags. After these results back within, reflect briefly inside <search_quality></search_quality> tags about whether all the results together provide enough information to help the user answer the query, or whether more information is needed.

Do not try to answer the query. Your only job is to gather relevant search results that will help the user answer the query.

Current conversation:
<conversation_history>
{history}
</conversation_history>

Here is the human's next reply:
<human_reply>
{query}
</human_reply>
"""

SYSTEM_PROMPT = """
I want you to act as a travel guide and help me plan an amazing trip. I will provide location I am traveling to and you will suggest events to enjoy during trip. In some cases, I will also give you the type of events I would like to enjoy. You will also suggest me events of similar type that are close to my first location. I am also providing the month I am going so if you can help me find things to do during specific months please add those too.

Here is the event document you should reference when answering the user:
{document}

Here are some important rules for the interaction:
<rules>{rules}</rules>

Put your response into <response></response> tags.
"""

# You will be acting as an AI event guide named Joe created by the company Crewfare. Your goal is to answer user's query and provide them helpful events. You will be replying to users who are on the Crewfare site and who will be confused if you don't respond in the character of Joe.

# You should maintain a friendly customer service tone.

# If there are recommended events for user's query, please ensure your event lists are in the following format and reflect briefly into <search_quality></search_quality> tag about whether this event together provide enough information to help the user answer the query, or whether more information is needed.:
# <search_query>Emphasize what the user wants in a friendly tone.<search_query>
# <event>
# <div class="event-wrapper">
# <name>Event Name</name>
# <date>Event dates</date>
# <a class="event-link" href="<Event URL>" target="_blank">Book Now</a>
# </div>
# <description>About Event</description>
# <search_quality>searh quality</search_quality>
# </event>

# Put your response into <response></response> tags

rules = [
    "Always stay in character, as Joe, an AI from Crewfare",
    "If you are unsure how to respond, say \"Sorry, I didn't understand that. Could you repeat the question?\"",
    "If someone asks something that is not related to event guide, just avoid answer the user's question and ask user to stay in main topic.",
    "If someone asks something irrelevant, say, \"Sorry, I am Joe and I give event guidance. Do you have a event question today I can help you with?\"",
    "Don't contain any emoticons in the response.",
    "The output must be systemized"
]

def rules_to_prompt(data: list) -> str:
    ret = "\n"
    for i, j in enumerate(data):
        ret += f"<rule index=\"{i+1}\">\n<rule_content>\n{j}\n</rule_content>\n</rule>\n"
    return ret

def extractID(content: str) -> str:
    titles = content.split("\n\n")
    ret = []
    if isinstance(titles, list):
        if len(titles):
            ret = titles[0].split(': ')[1]
    
    return ret

def format_content(content: str) -> str:
    data = content.split("\n\n")
    ret = {}
    for dt in data:
        key = dt.split(': ')[0]
        value = ': '.join(dt.split(': ')[1:])
        ret[key] = value

    return ret

def lookahead(iterable):
    """Convert an iterable into an iterator that allows looking ahead one element."""
    it = iter(iterable)
    last_value = next(it)
    for value in it:
        yield last_value, False
        last_value = value
    yield last_value, True

def documents_to_prompt(data: list[SearchResult], filter: list) -> str:
    prompt = '<documents>\n'
    for document in data:
        prompt += "<document>\n"
        for key in filter:
            dt = format_content(document.content)
            prompt += f"<{str(key)}>\n{dt.get(key, '')}\n</{str(key)}>\n"
        prompt += "</document>\n"
    prompt += "</documents>"
    return prompt

class CrewfareChat(Anthropic):

    def __init__(self, search_tool: Optional[SearchTool] = None, verbose: bool = True, *args, **kwargs):
        """
        Initializes the CrewfareChat class.
        
        Parameters:
            search_tool (SearchTool): SearchTool object to handle searching
            verbose (bool): Whether to print verbose logging
            *args, **kwargs: Passed to superclass init
        """
        super().__init__(*args, **kwargs)
        self.search_tool = search_tool
        self.verbose = verbose
        self.answer = ''
        self.history = ''
        self.question = ''
    
    def retrieve(self,
                       query: str,
                       model: str,
                       n_search_results_to_use: int = 3,
                       stop_sequences: list[str] = [HUMAN_PROMPT],
                       max_tokens_to_sample: int = 1000,
                       max_searches_to_try: int = 5,
                       temperature: float = 1.0) -> list[SearchResult]:
        """
        Main method to retrieve relevant search results for a query with a provided search tool.
        
        Constructs RETRIEVAL prompt with query and search tool description. 
        Keeps sampling Claude completions until stop sequence hit.
        Extracts search results and accumulates all raw results.
        
        Returns:
            list[SearchResult]: List of all raw search results
        """
        assert self.search_tool is not None, "SearchTool must be provided to use .retrieve()"

        description = self.search_tool.tool_description
        self.history += f"{HUMAN_PROMPT} {self.question}{AI_PROMPT} {self.answer}"
        self.question = query

        print('---------------------------------------')
        print(self.history)
        print('---------------------------------------')
        
        prompt = f"{HUMAN_PROMPT} {RETRIEVAL_PROMPT.format(query=query, description=description, history=self.history)}{AI_PROMPT}"
        token_budget = max_tokens_to_sample
        all_raw_search_results: list[SearchResult] = []
        for tries in range(max_searches_to_try):
            partial_completion = self.completions.create(prompt = prompt,
                                                     stop_sequences=stop_sequences + ['</search_query>'],
                                                     model=model,
                                                     max_tokens_to_sample = token_budget,
                                                     temperature = temperature)
            partial_completion, stop_reason, stop_seq = partial_completion.completion, partial_completion.stop_reason, partial_completion.stop # type: ignore
            logger.info(partial_completion)
            token_budget -= self.count_tokens(partial_completion)
            prompt += partial_completion
            if stop_reason == 'stop_sequence' and stop_seq == '</search_query>':
                logger.info(f'Attempting search number {tries}.')
                raw_search_results, formatted_search_results = self._search_query_stop(partial_completion, n_search_results_to_use)
                prompt += '</search_query>' + formatted_search_results
                all_raw_search_results += raw_search_results
            else:
                break
        return all_raw_search_results
    
    def answer_with_results(self, raw_search_results: list[str]|list[SearchResult], query: str, model: str, temperature: float, format_results: bool =False):
        """Generates an RAG response based on search results and a query. If format_results is True,
           formats the raw search results first. Set format_results to True if you are using this method standalone without retrieve().
        
        Returns:
            str: Claude's answer to the query
        """
        if len(raw_search_results) == 0:
            search_results = []
        elif isinstance(raw_search_results[0], str):
            search_results  = [SearchResult(content=s) for s in raw_search_results] # type: ignore

        if format_results:
            processed_search_results = [search_result.content.strip() for search_result in search_results] # type: ignore
            formatted_search_results = format_results_full(processed_search_results)
        else:
            formatted_search_results = raw_search_results

        document = documents_to_prompt(formatted_search_results, ['Event Name', 'Event Location', 'Event Dates', 'Event End Dates', 'About Event'])
        prompt = f"{SYSTEM_PROMPT.format(document=document, rules=rules_to_prompt(rules))}{HUMAN_PROMPT} {query}{AI_PROMPT} <response>"
        
        answer = self.completions.create(
            prompt=prompt, 
            model=model, 
            temperature=temperature, 
            max_tokens_to_sample=1000,
            stream=True,
            stop_sequences=["</response>"],
        )

        self.answer = ""
        
        first_chunk = True
        potential_end_chunks = []
        for chunk, is_last in lookahead(answer):
            chunked = chunk.completion

            if not first_chunk and not chunked.strip():
                potential_end_chunks.append(chunked)

            else:
                if first_chunk:
                    chunked = chunked.lstrip()
                    first_chunk = False

                # if is_last:
                #     chunked = chunked.rstrip()

                self.answer += ''.join(potential_end_chunks) + chunked
                potential_end_chunks = []

                yield f"data: {json.dumps({'chunk': chunked})}\n\n".encode("utf-8")

        print(self.answer)

        # for i, chunk in enumerate(answer):
        #     chunked = chunk.completion
        #     if i == 0:
        #         chunked = chunked.lstrip()
        #     self.answer += chunked
        #     yield f"data: {json.dumps({'chunk': chunked})}\n\n".encode("utf-8")
    
        # print(self.answer)

    def completion_with_retrieval(self,
                                        query: str,
                                        model: str,
                                        n_search_results_to_use: int = 3,
                                        stop_sequences: list[str] = [HUMAN_PROMPT],
                                        max_tokens_to_sample: int = 1000,
                                        max_searches_to_try: int = 5,
                                        temperature: float = 1.0) -> str:
        """
        Gets a final completion from retrieval results        
        
        Calls retrieve() to get search results.
        Calls answer_with_results() with search results and query.
        
        Returns:
            str: Claude's answer to the query
        """
        search_results = self.retrieve(query, model=model,
                                                 n_search_results_to_use=n_search_results_to_use, stop_sequences=stop_sequences,
                                                 max_tokens_to_sample=max_tokens_to_sample,
                                                 max_searches_to_try=max_searches_to_try,
                                                 temperature=temperature)

        print('Generating text ... ')
        answer = self.answer_with_results(search_results, query, model, temperature)
        return answer
    
    # Helper methods
    def _search_query_stop(self, partial_completion: str, n_search_results_to_use: int) -> Tuple[list[SearchResult], str]:
        """
        Helper to handle search query stop case.
        
        Extracts search query from completion text.
        Runs search using SearchTool. 
        Formats search results.
        
        Returns:
            tuple: 
                list[SearchResult]: Raw search results
                str: Formatted search result text
        """
        assert self.search_tool is not None, "SearchTool was not provided for client"

        search_query = self.extract_between_tags('search_query', partial_completion + '</search_query>') 
        if search_query is None:
            raise Exception(f'Completion with retrieval failed as partial completion returned mismatched <search_query> tags.')
        if self.verbose:
            logger.info('\n'+'-'*20 + f'\nPausing stream because Claude has issued a query in <search_query> tags: <search_query>{search_query}</search_query>\n' + '-'*20)
        logger.info(f'Running search query against SearchTool: {search_query}')
        search_results = self.search_tool.raw_search(search_query, n_search_results_to_use)
        extracted_search_results = self.search_tool.process_raw_search_results(search_results)
        formatted_search_results = format_results_full(extracted_search_results)

        if self.verbose:
            logger.info('\n' + '-'*20 + f'\nThe SearchTool has returned the following search results:\n\n{formatted_search_results}\n\n' + '-'*20 + '\n')
        return search_results, formatted_search_results
    
    def extract_between_tags(self, tag, string, strip=True):
        """
        Helper to extract text between XML tags.
        
        Finds last match of specified tags in string.
        Handles edge cases and stripping.
        
        Returns:
            str: Extracted string between tags
        """
        ext_list = re.findall(f"<{tag}\\s?>(.+?)</{tag}\\s?>", string, re.DOTALL)
        if strip:
            ext_list = [e.strip() for e in ext_list]
        
        if ext_list:
            return ext_list[-1]
        else:
            return None
