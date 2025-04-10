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


def classify_comment_sentiment_openai(comment_body, messages, client, model):
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
        temperature = 0
    )

    # Gets the content (sentiment) of the response
    comment_sentiment = response.choices[0].message.content.lower()
    print(comment_sentiment)

    # Appending the sentiment to the context of the conversation
    messages.append({
        "role": "assistant",
        "content": comment_sentiment
    })

    return comment_sentiment


def analyze_issue_sentiment_gpt(issue_title, issue_body, comments, client, model):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a GitHub issue sentiment analysis expert. "
                "Classify each comment's sentiment as 'positive', 'negative', or 'neutral'. "
                "Answer with one word only."
            )
        },
        {
            "role": "user",
            "content": f"The title of the issue is: {issue_title}"
        },
        {
            "role": "user",
            "content": f"The body of the issue is: {issue_body}"
        }
    ]

    results = []
    for comment in comments:
        comment_id, _, comment_body = comment

        print(f"Classifying comment {comment_id}...", end=' ')
        comment_sentiment = classify_comment_sentiment_openai(
            comment_body=comment_body, 
            messages=messages, 
            client=client, 
            model=model
        )

        results.append((comment_id, comment_sentiment))

    return results


def save_sentiments_gpt(sentiments,cursor):
    cursor.execute(
        """
        ALTER TABLE
            issue_comments_from_release
        ADD COLUMN IF NOT EXISTS
            sentiment_gpt_4o_mini TEXT;
        """
    )

    i = 0
    for sentiment in sentiments:
        try:
            comment_id, comment_sentiment = sentiment

            cursor.execute(
                """
                UPDATE 
                    issue_comments_from_release
                SET 
                    sentiment_gpt_4o_mini = %s
                WHERE
                    comment_id = %s;
                """,
                (comment_sentiment, comment_id)
            )
            i += 1
        except Exception as e:
            print(f"Error occurred with comment {sentiment}: {e}")

    print(f"{i} out of {len(sentiments)} comments successfully saved.")