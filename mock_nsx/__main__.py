"""Run the mock NSX Manager: `uv run --group mock python -m mock_nsx [--port 8443]`."""

from __future__ import annotations

import argparse
import datetime
import ipaddress
import tempfile
from pathlib import Path

import uvicorn


def _generate_self_signed_cert(tmp_dir: Path) -> tuple[Path, Path]:
    """Generate a throwaway self-signed cert so --tls exercises a real TLS handshake."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "mock-nsx")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    key_path = tmp_dir / "mock-nsx-key.pem"
    cert_path = tmp_dir / "mock-nsx-cert.pem"
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return key_path, cert_path


def main() -> None:
    # TLS is on by default: NsxtSession only ever speaks https:// (real NSX-T
    # Managers are HTTPS-only), so a plain-HTTP mock would be unreachable by
    # the client under test. --no-tls exists only for poking the mock with curl.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--no-tls", action="store_true", help="serve plain HTTP (curl debugging only)")
    args = parser.parse_args()

    ssl_keyfile: str | None = None
    ssl_certfile: str | None = None
    if not args.no_tls:
        tmp_dir = Path(tempfile.mkdtemp(prefix="mock-nsx-"))
        key_path, cert_path = _generate_self_signed_cert(tmp_dir)
        ssl_keyfile, ssl_certfile = str(key_path), str(cert_path)

    uvicorn.run(
        "mock_nsx.app:app",
        host=args.host,
        port=args.port,
        log_level="info",
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
    )


if __name__ == "__main__":
    main()
