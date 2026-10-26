"""Avatar MIME compatibility without calling storage or a database."""
import pytest
from app.routes.user_routes import _is_valid_avatar

PNG = b'\x89PNG\r\n\x1a\n' + b'example'
JPEG = b'\xff\xd8\xff' + b'example'
WEBP = b'RIFF' + b'\x00' * 4 + b'WEBP' + b'example'


@pytest.mark.parametrize('mime', [None, '', 'application/octet-stream', 'binary/octet-stream'])
@pytest.mark.parametrize('content', [PNG, JPEG, WEBP])
def test_generic_mime_uses_supported_signature(content, mime):
    assert _is_valid_avatar(content, mime)


@pytest.mark.parametrize('content,mime', [
    (JPEG, 'image/jpg'), (PNG, ' Image/PNG; charset=binary '),
    (WEBP, 'image/webp'),
])
def test_supported_mime_alias_and_parameters(content, mime):
    assert _is_valid_avatar(content, mime)


@pytest.mark.parametrize('content,mime', [
    (b'<html>invalid</html>', 'application/octet-stream'),
    (b'RIFF', 'image/webp'), (b'RIFF' + b'\x00' * 4 + b'WAVE', None),
    (PNG, 'text/html'), (JPEG, 'image/png'), (b'', None),
])
def test_invalid_or_mismatched_signature_is_rejected(content, mime):
    assert not _is_valid_avatar(content, mime)
