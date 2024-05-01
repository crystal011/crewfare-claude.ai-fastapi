# get_knowledge_description = """
# <tool_description>
# <tool_name>get_knowledge</tool_name>
# <description>
# Retrieve event information by querying based on location, dates, and key descriptors.
# </description>
# <parameters>
# <parameter>
# <name>date</name>
# <type>string</type>
# <description>
# Enter the date or range of dates when the event is scheduled to occur for time-specific searches. Return format should be "yyyy-mm-dd to yyyy-mm-dd". Default year is 2024. Relative dates will ignore like "this weekend", "after holiday", "this year", "next year", etc. If no date provided, enter empty string.
# </description>
# </parameter>
# <parameter>
# <name>location</name>
# <type>string</type>
# <description>
# Specify the geographic area or venue to localize the event search. If no location provided, enter empty string.
# </description>
# </parameter>
# <parameter>
# <name>description</name>
# <type>string</type>
# <description>
# List key descriptors or keywords related to the event to enhance search relevance in the knowledge base. If no description provided, enter empty string.
# </description>
# </parameter>
# </parameters>
# </tool_description>
# """

get_knowledge_description = """
<tool_description>
    <tool_name>get_knowledge</tool_name>
    <description>
        Retrieve event information by querying based on location, specific dates, key descriptors, and event categories.
    </description>
    <parameters>
        <parameter>
            <name>relative_date</name>
            <type>string</type>
            <description>
                Specify the relative dates for when the event is scheduled to occur. (e.g., this weekend, this year, in two years, ...)
            </description>
        </parameter>
        <parameter>
            <name>date</name>
            <type>string</type>
            <description>
                Specify the exact date or range of dates for when the event is scheduled to occur. Define dates format as "yyyy-mm-dd to yyyy-mm-dd". The system applies a default year of 2024 for unspecified dates. If the event date cannot be defined by a specific month or year and is instead a relative date (e.g., "this weekend", "after holiday", "this year", "next year"), leave the input as an empty string. If no date is provided, enter an empty string.
            </description>
        </parameter>
        <parameter>
            <name>location</name>
            <type>string</type>
            <description>
                Specify the geographic area or venue to localize the event search. If no location is provided, enter an empty string.
            </description>
        </parameter>
        <parameter>
            <name>description</name>
            <type>string</type>
            <description>
                Enter keywords or key descriptors related to the event to aid in search relevance.
            </description>
        </parameter>
        <parameter>
            <name>category</name>
            <type>[Adventure, Arts, Business, Culture, Fashion, Food, Holiday, Music, Sports, Tech, Wellness]</type>
            <description>
                Specify one or more event categories to refine the search. Categories should be comma-separated if multiple are included (e.g., "Sports,Music"). Allowed categories are Adventure, Arts, Business, Culture, Fashion, Food, Holiday, Music, Sports, Tech, and Wellness. Please select from these predefined categories only.
            </description>
        </parameter>
    </parameters>
</tool_description>
"""

# Accepted inputs include a specific month and year (e.g., "March 2024"), a year only (e.g., "2025"), or timeframes such as "mid-April".