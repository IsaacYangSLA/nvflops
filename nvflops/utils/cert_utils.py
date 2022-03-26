import datetime

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def serialize_pri_key(pri_key):
    return pri_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def serialize_cert(cert):
    return cert.public_bytes(serialization.Encoding.PEM)


class SimpleCert(object):
    def __init__(self, subject: str, ca=False, s_crt=None, s_prv=None):
        self.ca = ca
        self.s_crt = s_crt
        self.s_prv = s_prv
        self.crt = x509.load_pem_x509_certificate(s_crt, default_backend()) if s_crt else None
        self.prv = (
            serialization.load_pem_private_key(s_prv, password=None, backend=default_backend()) if s_prv else None
        )
        self.subject = subject
        self.issuer_simple_cert = None

    def set_issuer_simple_cert(self, issuer_simple_cert):
        self.issuer_simple_cert = issuer_simple_cert

    def create_cert(self):
        if self.s_crt and self.s_prv:
            return
        if self.ca:
            self.prv, pub_key = self._generate_keys()
            self.issuer = self.subject
            self.crt = self._generate_cert(self.subject, self.issuer, self.prv, pub_key, ca=True)
        elif self.issuer_simple_cert is not None:
            self.prv, pub_key = self._generate_keys()
            self.issuer = self.issuer_simple_cert.subject
            self.crt = self._generate_cert(self.subject, self.issuer, self.issuer_simple_cert.prv, pub_key)
        else:
            raise RuntimeError("No issuer cert found.")

    def serialize(self, pkcs12=False):
        if self.s_crt is None:
            self.s_crt = serialize_cert(self.crt)
        if self.s_prv is None:
            self.s_prv = serialize_pri_key(self.prv)
        self.s_pfx = serialization.pkcs12.serialize_key_and_certificates(
            self.subject.encode("utf-8"),
            self.prv,
            self.crt,
            None,
            serialization.BestAvailableEncryption(self.subject.encode("utf-8")),
        )

    def get_pri_key_cert(self, participant):
        pri_key, pub_key = self._generate_keys()
        subject = participant.subject
        cert = self._generate_cert(subject, self.issuer, self.pri_key, pub_key)
        return pri_key, cert

    def _generate_keys(self):
        pri_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        pub_key = pri_key.public_key()
        return pri_key, pub_key

    def _generate_cert(self, subject, issuer, signing_pri_key, subject_pub_key, valid_days=360, ca=False):
        x509_subject = self._x509_name(subject)
        x509_issuer = self._x509_name(issuer)
        builder = (
            x509.CertificateBuilder()
            .subject_name(x509_subject)
            .issuer_name(x509_issuer)
            .public_key(subject_pub_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(
                # Our certificate will be valid for 360 days
                datetime.datetime.utcnow()
                + datetime.timedelta(days=valid_days)
                # Sign our certificate with our private key
            )
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(subject)]), critical=False)
        )
        if ca:
            builder = (
                builder.add_extension(
                    x509.SubjectKeyIdentifier.from_public_key(subject_pub_key),
                    critical=False,
                )
                .add_extension(
                    x509.AuthorityKeyIdentifier.from_issuer_public_key(subject_pub_key),
                    critical=False,
                )
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=False)
            )
        return builder.sign(signing_pri_key, hashes.SHA256(), default_backend())

    def _x509_name(self, cn_name, org_name=None):
        name = [x509.NameAttribute(NameOID.COMMON_NAME, cn_name)]
        if org_name is not None:
            name.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name))
        return x509.Name(name)
