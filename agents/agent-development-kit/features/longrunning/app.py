from flask import Flask, render_template, request, jsonify, session, redirect
import uuid
from datetime import datetime
import os
import logging

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for escalated conversations
# Structure: {conversation_id: {question: str, timestamp: datetime, response: str or None}}
escalated_conversations = {}

@app.route('/')
def index():
    """Admin dashboard to see all escalated conversations"""
    return render_template('dashboard.html', conversations=escalated_conversations)

@app.route('/escalate', methods=['POST'])
def escalate():
    """API endpoint for the agent to escalate a question to a human"""
    logger.info(f"Received escalation request with headers: {request.headers}")
    
    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
            
        question = data.get('question')
        
        if not question:
            logger.error("Question is required but missing")
            return jsonify({'error': 'Question is required'}), 400
        
        # Generate a unique ID for this conversation
        conversation_id = str(uuid.uuid4())
        
        # Store the question with metadata
        escalated_conversations[conversation_id] = {
            'question': question,
            'timestamp': datetime.now(),
            'response': None,
            'status': 'pending'
        }
        
        logger.info(f"Successfully escalated question with ID: {conversation_id}")
        
        response_data = {
            'conversation_id': conversation_id,
            'status': 'escalated',
            'message': 'Successfully escalated to human'
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.exception(f"Error in escalate endpoint: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/respond/<conversation_id>', methods=['GET', 'POST'])
def respond(conversation_id):
    """Human interface to respond to an escalated conversation"""
    if conversation_id not in escalated_conversations:
        return render_template('error.html', message='Conversation not found'), 404
    
    conversation = escalated_conversations[conversation_id]
    
    if request.method == 'POST':
        response = request.form.get('response')
        if response:
            conversation['response'] = response
            conversation['status'] = 'completed'
            return redirect('/')
    
    return render_template('respond.html', conversation_id=conversation_id, conversation=conversation)

@app.route('/check/<conversation_id>', methods=['GET'])
def check_status(conversation_id):
    """API endpoint for the agent to check if a human has responded"""
    if conversation_id not in escalated_conversations:
        return jsonify({'error': 'Conversation not found'}), 404
    
    conversation = escalated_conversations[conversation_id]
    
    return jsonify({
        'status': conversation['status'],
        'response': conversation['response'] if conversation['status'] == 'completed' else None
    })

@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """API endpoint to get all conversations"""
    result = {}
    for id, convo in escalated_conversations.items():
        result[id] = {
            'question': convo['question'],
            'timestamp': convo['timestamp'].isoformat(),
            'status': convo['status'],
            'response': convo['response']
        }
    return jsonify(result)

@app.route('/test', methods=['GET'])
def test_connection():
    """Test endpoint to verify the API is working"""
    return jsonify({
        'status': 'success',
        'message': 'Flask app is running correctly'
    })

if __name__ == '__main__':
    logger.info(f"Starting Flask app on port {os.environ.get('PORT', 5000)}")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))