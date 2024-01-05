#!/bin/bash

# Initialize x_chat_history_value with an empty string at the start
x_chat_history_value=""
NGROK_URL="https://787f-18-234-252-53.ngrok-free.app"

# Function to perform search query
search_query() {
    echo "Enter your search query:"
    read search

    curl -X GET -G "$NGROK_URL/query/" -H "accept: application/json" --data-urlencode "search=$search"

    echo -e
}

# Function to perform chat
chat_question() {
    while true; do
        echo "Enter your question for the chat (or type 'exit' to quit):"
        echo -n "User: "
        read question

    if [[ "$question" == "exit" ]]; then
        break
    fi

    # Capture the response including headers and body
    response=$(curl -s -i -X GET -G "$NGROK_URL/chat/" -H "accept: application/json" --data-urlencode "q=$question" --data-urlencode "chatHistory=$x_chat_history_value")

    # Extract the response body without headers
    response_body=$(echo "$response" | awk '/^\r$/{flag=1;next}/^$/{flag=1;next}flag')

    echo -n "Assistant: "
    echo "$response_body"
    echo -e

    # Extract the X-Chat-History header value from this response
    new_x_chat_history_value=$(echo "$response" | awk '/^x-chat-history:/{print $2}' | tr -d '\r')
    
    # Display the extracted X-Chat-History header value only if it's not empty
    if [ ! -z "$new_x_chat_history_value" ]; then
        echo "X-Chat-History value: $new_x_chat_history_value"
        echo -e
      
        # Update x_chat_history_value with the new value for the next request
        x_chat_history_value="$new_x_chat_history_value"
    else
        echo "No X-Chat-History value found."
    fi
    done
}

# Main interaction with user
echo "Welcome! Do you want to 'search' or 'chat'?"
read choice

case $choice in
    [Ss]earch)
        search_query
        ;;
    [Cc]hat)
        chat_question
        ;;
    *)
        echo "Invalid option. Please enter either 'Search' or 'Chat'."
        ;;
esac
