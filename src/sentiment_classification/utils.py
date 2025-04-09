def get_comments_by_issue_id(issue_id, cursor):
    cursor.execute(
        """
        SELECT 
            comment_id,
            created_at,
            body
        FROM
            issue_comments_from_release
        WHERE 
            issue_id = %s
        ORDER BY
            created_at;
        """,(issue_id,)
    )
    comments = cursor.fetchall()

    return comments

def classify_comment_sentiment_gpt(comment_body, messages, client, model):
    prompt = f"Classify the sentiment of this comment: {comment_body}"

    # Appending this prompt to messages
    messages.append({
        "role": "user",
        "content": prompt
    })
    
    # Sends the prompt and gets the response
    response = client.chat.completions.create(
        model = model,
        messages = messages,
        temperature = 0.2
    )

    # Gets the content (sentiment) of the response
    comment_sentiment = response.choices[0].message.content.lower()

    return comment_sentiment