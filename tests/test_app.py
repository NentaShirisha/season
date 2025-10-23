import io
import os
import json
import tempfile
import pytest

from app import app, db, Record, init_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    # use a temp database
    db_file = tmp_path / 'test.db'
    monkeypatch.setenv('WERKZEUG_RUN_MAIN', 'true')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
    app.config['TESTING'] = True
    with app.test_client() as c:
        with app.app_context():
            db.create_all()
        yield c


def test_upload_and_predict(client):
    csv = io.BytesIO(b"date,season,medicine,quantity\n2023-12-01,Winter,Paracetamol,100\n2024-12-01,Winter,Paracetamol,120\n")
    data = {'file': (csv, 'data.csv')}
    rv = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    j = rv.get_json()
    assert j['inserted'] == 2

    rv2 = client.get('/api/prediction?season=Winter')
    assert rv2.status_code == 200
    pj = rv2.get_json()
    assert 'Paracetamol' in pj['prediction']


def test_records_and_validation(client):
    # insert some records including an invalid row
    csv = io.BytesIO(b"date,season,medicine,quantity\n2022-01-01,Winter,A,10\n2022-01-02,Winter,B,-5\n")
    data = {'file': (csv, 'data2.csv')}
    rv = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    j = rv.get_json()
    # one valid row, one invalid (negative quantity)
    assert j['inserted'] == 1
    assert 'errors' in j and len(j['errors']) == 1

    # records endpoint should return at least the valid record
    rv2 = client.get('/api/records?page=1&per_page=10')
    assert rv2.status_code == 200
    rows = rv2.get_json()
    assert any(r['medicine'] == 'A' for r in rows)

def test_pagination(client):
    # bulk insert 25 records
    buf = io.BytesIO()
    buf.write(b"date,season,medicine,quantity\n")
    for i in range(25):
        line = f"2021-01-{(i%28)+1:02d},Winter,M{i},{i+1}\n".encode()
        buf.write(line)
    buf.seek(0)
    data = {'file': (buf, 'bulk.csv')}
    rv = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    j = rv.get_json()
    # ensure some inserted
    assert j['inserted'] >= 25

    # page 1 should have per_page items
    rv2 = client.get('/api/records?page=1&per_page=10')
    rows = rv2.get_json()
    assert len(rows) <= 10 and len(rows) > 0

