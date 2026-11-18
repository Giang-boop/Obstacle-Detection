import datetime
import ipaddress
import json
import os
import socket

from server.config import INSTANCE_DIR

CERT_DIR = os.path.join(INSTANCE_DIR, "certs")
CERT_FILE = os.path.join(CERT_DIR, "blindassist-cert.pem")
KEY_FILE = os.path.join(CERT_DIR, "blindassist-key.pem")
NAMES_FILE = os.path.join(CERT_DIR, "blindassist-names.json")


def lan_ip_addresses():
    addresses = {"127.0.0.1"}
    try:
        for address in socket.gethostbyname_ex(socket.gethostname())[2]:
            addresses.add(address)
    except OSError:
        pass
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        addresses.add(probe.getsockname()[0])
    except OSError:
        pass
    finally:
        probe.close()
    return sorted(address for address in addresses if not address.startswith("169.254."))


def certificate_names():
    return {
        "dns": sorted({"localhost", socket.gethostname()}),
        "ip": lan_ip_addresses(),
    }


def existing_names():
    try:
        with open(NAMES_FILE, encoding="utf-8") as names_file:
            return json.load(names_file)
    except (OSError, ValueError):
        return None


def certificate_is_current(names):
    if not (os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)):
        return False
    saved = existing_names()
    if not saved:
        return False
    return set(names["ip"]) <= set(saved.get("ip", [])) and set(names["dns"]) <= set(saved.get("dns", []))


def create_self_signed_certificate(names):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    os.makedirs(CERT_DIR, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "BlindAssist máy chủ nội bộ"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "BlindAssist Nhóm 11"),
    ])
    alt_names = [x509.DNSName(name) for name in names["dns"]]
    alt_names += [x509.IPAddress(ipaddress.ip_address(address)) for address in names["ip"]]
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    with open(CERT_FILE, "wb") as cert_file:
        cert_file.write(certificate.public_bytes(serialization.Encoding.PEM))
    with open(NAMES_FILE, "w", encoding="utf-8") as names_file:
        json.dump(names, names_file, ensure_ascii=False, indent=2)


def ensure_certificate():
    names = certificate_names()
    if not certificate_is_current(names):
        saved = existing_names() or {}
        merged = {
            "dns": sorted(set(names["dns"]) | set(saved.get("dns", []))),
            "ip": sorted(set(names["ip"]) | set(saved.get("ip", []))),
        }
        create_self_signed_certificate(merged)
        names = merged
    return CERT_FILE, KEY_FILE, names
