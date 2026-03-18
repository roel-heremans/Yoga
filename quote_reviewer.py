#!/usr/bin/env python3
"""
Quote Reviewer Web UI

A simple web interface for reviewing, approving, adjusting, and rejecting quotes.
"""

import json
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Get base paths
BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / 'assets' / '10_knowledge'


def load_quotes_file(group_name: str) -> dict:
    """Load quotes JSON file for a group."""
    quotes_file = KNOWLEDGE_DIR / group_name / 'quotes.json'
    if not quotes_file.exists():
        return {}
    
    with open(quotes_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_quotes_file(group_name: str, data: dict):
    """Save quotes JSON file for a group."""
    quotes_file = KNOWLEDGE_DIR / group_name / 'quotes.json'
    quotes_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(quotes_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_quote_status(quote):
    """Get quote status: pending, accepted, or rejected."""
    # Support both old format (approved boolean) and new format (status field)
    if 'status' in quote:
        status = quote['status'].lower()
        if status in ['pending', 'accepted', 'rejected']:
            return status
    # Legacy support: convert approved boolean to status
    if quote.get('approved', False):
        return 'accepted'
    return 'pending'


def get_literature_groups():
    """Get list of literature groups."""
    if not KNOWLEDGE_DIR.exists():
        return []
    
    groups = []
    for item in KNOWLEDGE_DIR.iterdir():
        if item.is_dir():
            quotes_file = item / 'quotes.json'
            if quotes_file.exists():
                data = load_quotes_file(item.name)
                quotes = data.get('quotes', [])
                total_quotes = len(quotes)
                accepted_quotes = sum(1 for q in quotes if get_quote_status(q) == 'accepted')
                rejected_quotes = sum(1 for q in quotes if get_quote_status(q) == 'rejected')
                pending_quotes = total_quotes - accepted_quotes - rejected_quotes
                groups.append({
                    'name': item.name,
                    'display_name': data.get('source', item.name),
                    'author': data.get('author', ''),
                    'total_quotes': total_quotes,
                    'accepted_quotes': accepted_quotes,
                    'rejected_quotes': rejected_quotes,
                    'pending_quotes': pending_quotes,
                    'extraction_method': data.get('extraction_method', 'simple')
                })
    
    return sorted(groups, key=lambda x: x['name'])


@app.route('/')
def index():
    """Main page showing literature groups."""
    groups = get_literature_groups()
    return render_template('index.html', groups=groups)


@app.route('/api/groups')
def api_groups():
    """API endpoint to get literature groups."""
    return jsonify(get_literature_groups())


@app.route('/review/<group_name>')
def review_group(group_name):
    """Review page for a specific group."""
    data = load_quotes_file(group_name)
    if not data:
        return f"Group '{group_name}' not found or has no quotes", 404
    
    return render_template('review.html', 
                         group_name=group_name,
                         source=data.get('source', group_name),
                         author=data.get('author', ''),
                         extraction_method=data.get('extraction_method', 'simple'))


@app.route('/api/quotes/<group_name>')
def api_quotes(group_name):
    """API endpoint to get quotes for a group."""
    data = load_quotes_file(group_name)
    if not data:
        return jsonify({'error': 'Group not found'}), 404
    
    quotes = data.get('quotes', [])
    
    # Get filter parameters
    filter_status = request.args.get('status')  # pending, accepted, rejected
    filter_type = request.args.get('type')
    min_score = request.args.get('min_score', type=float)
    search = request.args.get('search', '').lower()
    
    # Filter quotes
    filtered_quotes = quotes
    if filter_status:
        status_val = filter_status.lower()
        filtered_quotes = [q for q in quotes if get_quote_status(q) == status_val]
    
    if filter_type:
        filtered_quotes = [q for q in filtered_quotes if q.get('type') == filter_type]
    
    if min_score is not None:
        filtered_quotes = [q for q in filtered_quotes if q.get('importance_score', 0) >= min_score]
    
    if search:
        filtered_quotes = [q for q in filtered_quotes if search in q.get('text', '').lower()]
    
    # Sort by importance score (descending)
    filtered_quotes.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
    
    # Count by status
    accepted_count = sum(1 for q in quotes if get_quote_status(q) == 'accepted')
    rejected_count = sum(1 for q in quotes if get_quote_status(q) == 'rejected')
    pending_count = len(quotes) - accepted_count - rejected_count
    
    return jsonify({
        'quotes': filtered_quotes,
        'total': len(quotes),
        'accepted': accepted_count,
        'rejected': rejected_count,
        'pending': pending_count,
        'filtered': len(filtered_quotes)
    })


@app.route('/api/quotes/<group_name>/<quote_id>', methods=['PUT'])
def update_quote(group_name, quote_id):
    """API endpoint to update a quote."""
    data = load_quotes_file(group_name)
    if not data:
        return jsonify({'error': 'Group not found'}), 404
    
    quotes = data.get('quotes', [])
    quote_index = None
    
    for i, quote in enumerate(quotes):
        if quote.get('id') == quote_id:
            quote_index = i
            break
    
    if quote_index is None:
        return jsonify({'error': 'Quote not found'}), 404
    
    # Get update data from request
    update_data = request.get_json()
    
    # Update quote fields
    if 'status' in update_data:
        status = update_data['status'].lower()
        if status in ['pending', 'accepted', 'rejected']:
            quotes[quote_index]['status'] = status
            # Remove old approved field if it exists (migration)
            if 'approved' in quotes[quote_index]:
                del quotes[quote_index]['approved']
    # Legacy support: convert approved boolean to status
    elif 'approved' in update_data:
        approved = update_data['approved']
        quotes[quote_index]['status'] = 'accepted' if approved else 'pending'
        # Remove old approved field
        if 'approved' in quotes[quote_index]:
            del quotes[quote_index]['approved']
    
    if 'text' in update_data:
        quotes[quote_index]['text'] = update_data['text']
    if 'notes' in update_data:
        quotes[quote_index]['notes'] = update_data['notes']
    
    # Save updated data
    data['quotes'] = quotes
    save_quotes_file(group_name, data)
    
    return jsonify({'success': True, 'quote': quotes[quote_index]})


@app.route('/api/quotes/<group_name>/bulk', methods=['POST'])
def bulk_update_quotes(group_name):
    """API endpoint for bulk updates."""
    data = load_quotes_file(group_name)
    if not data:
        return jsonify({'error': 'Group not found'}), 404
    
    quotes = data.get('quotes', [])
    updates = request.get_json()
    
    updated_count = 0
    for update in updates:
        quote_id = update.get('id')
        for i, quote in enumerate(quotes):
            if quote.get('id') == quote_id:
                if 'status' in update:
                    status = update['status'].lower()
                    if status in ['pending', 'accepted', 'rejected']:
                        quotes[i]['status'] = status
                        # Remove old approved field if it exists
                        if 'approved' in quotes[i]:
                            del quotes[i]['approved']
                elif 'approved' in update:
                    # Legacy support
                    approved = update['approved']
                    quotes[i]['status'] = 'accepted' if approved else 'pending'
                    if 'approved' in quotes[i]:
                        del quotes[i]['approved']
                if 'text' in update:
                    quotes[i]['text'] = update['text']
                if 'notes' in update:
                    quotes[i]['notes'] = update['notes']
                updated_count += 1
                break
    
    # Save updated data
    data['quotes'] = quotes
    save_quotes_file(group_name, data)
    
    return jsonify({'success': True, 'updated': updated_count})


@app.route('/api/stats/<group_name>')
def api_stats(group_name):
    """API endpoint to get statistics for a group."""
    data = load_quotes_file(group_name)
    if not data:
        return jsonify({'error': 'Group not found'}), 404
    
    quotes = data.get('quotes', [])
    
    accepted_count = sum(1 for q in quotes if get_quote_status(q) == 'accepted')
    rejected_count = sum(1 for q in quotes if get_quote_status(q) == 'rejected')
    pending_count = len(quotes) - accepted_count - rejected_count
    
    stats = {
        'total': len(quotes),
        'accepted': accepted_count,
        'rejected': rejected_count,
        'pending': pending_count,
        'by_type': {},
        'avg_score': 0,
        'high_score': 0
    }
    
    if quotes:
        # Count by type
        for quote in quotes:
            quote_type = quote.get('type', 'quote')
            stats['by_type'][quote_type] = stats['by_type'].get(quote_type, 0) + 1
        
        # Calculate average score
        scores = [q.get('importance_score', 0) for q in quotes]
        stats['avg_score'] = sum(scores) / len(scores) if scores else 0
        stats['high_score'] = max(scores) if scores else 0
    
    return jsonify(stats)


@app.route('/output/<path:filepath>')
def serve_output(filepath):
    """Serve generated quote card files (output/quote_cards/...) for review."""
    output_dir = BASE_DIR / 'output'
    path = Path(filepath)
    if path.is_absolute() or '..' in filepath:
        return '', 404
    full = output_dir / filepath
    if not full.exists() or not full.is_file():
        return '', 404
    return send_from_directory(output_dir, filepath, as_attachment=False)


@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests to prevent 404 errors."""
    return '', 204  # No content


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = BASE_DIR / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Disable CSP for local development (or configure it properly)
    @app.after_request
    def set_response_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Remove or relax CSP if it's causing issues
        # response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval';"
        return response
    
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*60)
    print("Quote Reviewer Web UI")
    print("="*60)
    print(f"\nStarting server at http://localhost:{port}")
    print(f"Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=port)
