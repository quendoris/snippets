"""Privacy archive tests: wrong key, tamper resistance, Unicode, atomic no-clobber."""
import io
from pathlib import Path
import tempfile
import unittest
import zipfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from qar import encrypt, decrypt, HEADER_LEN


class QARTests(unittest.TestCase):
    def test_roundtrip_and_wrong_password_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "разговор с символами.txt"
            src.write_text('Тест: ÷¿éÜ\\\'ßß🎙️' * 900, encoding="utf-8")
            key = 'an intentionally long passphrase: ÷§Ωλ\\\'\\\"🧪'.encode('utf-8')
            enc = base / "snapshot.qar"
            dec = base / "restored.zip"
            encrypt(src, enc, key)
            self.assertEqual(enc.read_bytes()[:4], b"QAR1")
            self.assertEqual(enc.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(src.read_bytes()[:40], enc.read_bytes())
            with self.assertRaisesRegex(ValueError, 'Authentication failed'):
                decrypt(enc, dec, b'not the key')
            self.assertFalse(dec.exists())
            tampered = bytearray(enc.read_bytes())
            tampered[HEADER_LEN + 4] ^= 16
            (base / 'tampered.qar').write_bytes(tampered)
            with self.assertRaisesRegex(ValueError, 'Authentication failed'):
                decrypt(base / 'tampered.qar', dec, key)
            self.assertFalse(dec.exists())
            decrypt(enc, dec, key)
            with zipfile.ZipFile(io.BytesIO(dec.read_bytes())) as z:
                self.assertEqual(z.namelist(), [src.name])
                self.assertEqual(z.read(src.name), src.read_bytes())
            with self.assertRaises(FileExistsError):
                encrypt(src, enc, key)

    def test_truncated_or_invalid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'broken.qar').write_bytes(b'QAR1' + b'x' * 6)
            with self.assertRaisesRegex(ValueError, 'header'):
                decrypt(base / 'broken.qar', base / 'out.zip', b'secret')
            self.assertFalse((base / 'out.zip').exists())

    def test_reject_symlink_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / 'original.txt'
            src.write_text('do not read through links', encoding='utf8')
            link = base / 'link.txt'
            link.symlink_to(src)
            with self.assertRaisesRegex(ValueError, 'non-symlink'):
                encrypt(link, base / 'out.qar', b'secret')
            self.assertFalse((base / 'out.qar').exists())

    def test_distinct_ciphertexts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / 'chat.html'
            src.write_text('hello', encoding='utf-8')
            encrypt(src, base / 'one.qar', b'same key')
            encrypt(src, base / 'two.qar', b'same key')
            self.assertNotEqual((base / 'one.qar').read_bytes(), (base / 'two.qar').read_bytes())


if __name__ == '__main__':
    unittest.main()
