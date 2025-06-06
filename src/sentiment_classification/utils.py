import logging
from log_config import configure_logging

configure_logging()

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
        temperature = 0.2
    )

    # Gets the content (sentiment) of the response
    comment_sentiment = response.choices[0].message.content.lower()
    logging.info(f"Sentiment of the comment is: {comment_sentiment}")

    # Appending the sentiment to the context of the conversation
    messages.append({
        "role": "assistant",
        "content": comment_sentiment
    })

    return comment_sentiment


def analyze_issue_sentiment_openai(issue_title, issue_body, comments, client, model):
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

        logging.info(f"Classifying comment {comment_id}...")
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
        except Exception as e:
            logging.error(f"Error occurred with comment {sentiment}: {e}")
            continue


def save_sentiments_ds(sentiments,cursor):
    cursor.execute(
        """
        ALTER TABLE
            issue_comments_from_release
        ADD COLUMN IF NOT EXISTS
            sentiment_deepseek_v3 TEXT;
        """
    )

    for sentiment in sentiments:
        try:
            comment_id, comment_sentiment = sentiment

            cursor.execute(
                """
                UPDATE 
                    issue_comments_from_release
                SET 
                    sentiment_deepseek_v3 = %s
                WHERE
                    comment_id = %s;
                """,
                (comment_sentiment, comment_id)
            )
        except Exception as e:
            logging.error(f"Error occurred with comment {sentiment}: {e}")
            continue
        

def save_sentiments_gemini(sentiments,cursor):
    try:
        cursor.execute(
            """
            ALTER TABLE
                issue_comments_from_release
            ADD COLUMN IF NOT EXISTS
                sentiment_gemini_2_0_flash TEXT;
            """
        )
    except Exception as e:
        logging.error(f"Error occurred when altering the table: {e}")
        
    i = 1
    for sentiment in sentiments:
        logging.info(f"Trying to save sentiment ({i}/{len(sentiments)})...")
        try:
            comment_id, comment_sentiment = sentiment

            cursor.execute(
                """
                UPDATE 
                    issue_comments_from_release
                SET 
                    sentiment_gemini_2_0_flash = %s
                WHERE
                    comment_id = %s;
                """,
                (comment_sentiment, comment_id)
            )

            logging.info("saved!")
            i += 1
        except Exception as e:
            logging.error(f"Error occurred with comment {sentiment}: {e}")
            continue