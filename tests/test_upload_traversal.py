import io, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from sau_backend import app
import sau_backend

@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "videoFile").mkdir()
    monkeypatch.setattr(sau_backend, "BASE_DIR", tmp_path)
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c, tmp_path

def test_upload_rejects_traversal(client):
    c, base = client
    data = {'file': (io.BytesIO(b'x'), '../../evil.mp4')}
    r = c.post('/upload', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    saved = r.get_json()['data']
    assert '..' not in saved and '/' not in saved
    assert (base / 'videoFile' / saved).exists()

def test_upload_normal(client):
    c, _ = client
    data = {'file': (io.BytesIO(b'hello'), 'video.mp4')}
    r = c.post('/upload', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    assert r.get_json()['data'].endswith('_video.mp4')

def test_uploadsave_rejects_empty_after_sanitize(client):
    c, _ = client
    data = {'file': (io.BytesIO(b'x'), '../../../')}
    r = c.post('/uploadSave', data=data, content_type='multipart/form-data')
    assert r.status_code == 400

def test_getfile_blocks_traversal(client):
    c, _ = client
    r = c.get('/getFile?filename=../../etc/passwd')
    assert r.status_code == 400
