from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import os
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
import io

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'data.db')

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    season = db.Column(db.String(32), nullable=False)
    medicine = db.Column(db.String(128), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'season': self.season,
            'medicine': self.medicine,
            'quantity': self.quantity,
        }


def init_db():
    if not os.path.exists(DB_PATH):
        db.create_all()


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/upload', methods=['POST'])
def upload():
    # Accept file upload (CSV) or JSON array
    try:
        if 'file' in request.files:
            f = request.files['file']
            filename = secure_filename(f.filename or 'upload.csv')
            data = f.read()
            df = pd.read_csv(io.BytesIO(data))
        else:
            payload = request.get_json()
            if not isinstance(payload, list):
                return jsonify({'error': 'JSON payload must be a list of records'}), 400
            df = pd.DataFrame(payload)
    except Exception as e:
        return jsonify({'error': f'failed to parse CSV/JSON: {str(e)}'}), 400

    # validate required columns
    required = {'date', 'season', 'medicine', 'quantity'}
    if not required.issubset(set(df.columns)):
        return jsonify({'error': 'CSV must contain date,season,medicine,quantity columns'}), 400

    # convert and insert with validation
    inserted = 0
    errors = []
    for idx, row in df.iterrows():
        try:
            d = pd.to_datetime(row['date'], errors='raise').date()
            season = str(row['season']).strip()
            medicine = str(row['medicine']).strip()
            qty = int(row['quantity'])
            if qty < 0:
                raise ValueError('quantity must be non-negative')
            if not season or not medicine:
                raise ValueError('season and medicine must be non-empty')
        except Exception as e:
            errors.append({'row': int(idx), 'error': str(e)})
            continue
        r = Record(date=d, season=season, medicine=medicine, quantity=qty)
        db.session.add(r)
        inserted += 1
    db.session.commit()
    return jsonify({'inserted': inserted, 'errors': errors})


@app.route('/api/records', methods=['GET'])
def list_records():
    # simple pagination
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
    except Exception:
        return jsonify({'error': 'page and per_page must be integers'}), 400
    q = Record.query.order_by(Record.date.desc())
    items = q.offset((page-1)*per_page).limit(per_page).all()
    return jsonify([r.to_dict() for r in items])


@app.route('/api/prediction', methods=['GET'])
def prediction():
    # Predict total required quantity per medicine for a given season
    season = request.args.get('season')
    if not season:
        return jsonify({'error': 'season query param required'}), 400

    # aggregate historical totals per year for the given season
    rows = db.session.query(
        func.strftime('%Y', Record.date).label('year'),
        Record.medicine,
        func.sum(Record.quantity).label('total')
    ).filter(Record.season == season).group_by('year', Record.medicine).all()

    if not rows:
        return jsonify({'prediction': {}, 'notes': 'no historical data for that season'}), 200

    # Transform to dataframe
    data = [{'year': r.year, 'medicine': r.medicine, 'total': r.total} for r in rows]
    df = pd.DataFrame(data)

    # For each medicine, compute average growth rate year-over-year and project next season requirement
    preds = {}
    for med, group in df.groupby('medicine'):
        g = group.sort_values('year')
        totals = g['total'].astype(float).values
        years = g['year'].values
        # if only one year, use that value as prediction
        if len(totals) == 1:
            pred = float(totals[0])
        else:
            # compute simple average year-over-year growth ratio
            ratios = []
            for i in range(1, len(totals)):
                if totals[i-1] == 0:
                    ratios.append(1.0)
                else:
                    ratios.append(totals[i]/totals[i-1])
            avg_ratio = sum(ratios)/len(ratios)
            pred = totals[-1] * avg_ratio
        preds[med] = {
            'predicted_quantity': round(pred, 2),
            'historical_years': len(totals),
            'last_total': float(totals[-1])
        }

    # Determine actions (increase/decrease) compared to last year
    actions = {}
    for med, meta in preds.items():
        last = meta['last_total']
        pred = meta['predicted_quantity']
        if pred > last * 1.05:
            actions[med] = 'increase'
        elif pred < last * 0.95:
            actions[med] = 'decrease'
        else:
            actions[med] = 'hold'

    return jsonify({'prediction': preds, 'actions': actions})


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
