from flask import Flask, request, jsonify
import boto3
import os

app = Flask(__name__)

SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")

sns_client = boto3.client('sns', region_name='us-east-2')


@app.route('/notify', methods=['POST'])
def send_notification():
    try:
        data = request.json
        item_id = data.get("item_id")
        review = data.get("review")
        rating = data.get("rating")

        if not item_id or not review or not rating:
            return jsonify({"error": "Missing required fields: item_id, review, or rating"}), 400

        sns_message = {
            "item_id": item_id,
            "review": review,
            "rating": rating
        }
        sns_response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=str(sns_message),
            Subject="New Review Notification"
        )
        print(f"Published to SNS: {sns_response}")

        return jsonify({"message": "Notification sent successfully!"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
