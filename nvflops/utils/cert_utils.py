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
    def __init__(self, subject: str, s_crt=None, s_prv=None):
        self.s_crt = s_crt
        self.s_prv = s_prv
        self.crt = x509.load_pem_x509_certificate(s_crt, default_backend()) if s_crt else None
        self.prv = (
            serialization.load_pem_private_key(s_prv, password=None, backend=default_backend()) if s_prv else None
        )
        self.pub = self.prv.public_key() if self.prv else None
        self.subject = subject
        self.issuer_simple_cert = None

    def set_issuer_simple_cert(self, issuer_simple_cert):
        self.issuer_simple_cert = issuer_simple_cert

    def create_cert(self, type):
        if self.s_crt and self.s_prv:
            return
        self.prv, self.pub = self._generate_keys()
        if type == "root":
            self.issuer = self
        elif self.issuer_simple_cert is not None:
            self.issuer = self.issuer_simple_cert
        else:
            raise RuntimeError("No issuer cert found.")
        self.crt = self._generate_cert(self.subject, self.issuer, self.issuer.prv, type=type)
        self.sha1_fingerprint_str = self.crt.fingerprint(hashes.SHA1()).hex()

    def serialize(self, pkcs12=False):
        if self.s_crt is None:
            self.s_crt = serialize_cert(self.crt)
        if self.s_prv is None:
            self.s_prv = serialize_pri_key(self.prv)
        if pkcs12:
            self.s_pfx = serialization.pkcs12.serialize_key_and_certificates(
                self.subject.encode("utf-8"),
                self.prv,
                self.crt,
                None,
                serialization.BestAvailableEncryption(self.subject.encode("utf-8")),
            )

    def _generate_keys(self):
        pri_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        pub_key = pri_key.public_key()
        return pri_key, pub_key

    def _generate_cert(self, subject_name, issuer_cert, signing_pri_key, type, valid_days=360):
        x509_subject = self._x509_name(subject_name)
        x509_issuer = self._x509_name(issuer_cert.subject)
        builder = (
            x509.CertificateBuilder()
            .subject_name(x509_subject)
            .issuer_name(x509_issuer)
            .public_key(self.pub)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(
                # Our certificate will be valid for 360 days
                datetime.datetime.utcnow()
                + datetime.timedelta(days=valid_days)
                # Sign our certificate with our private key
            )
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(subject_name)]), critical=False)
        )
        if type == "root":
            builder = (
                builder.add_extension(
                    x509.SubjectKeyIdentifier.from_public_key(self.pub),
                    critical=False,
                )
                .add_extension(
                    x509.AuthorityKeyIdentifier.from_issuer_public_key(self.pub),
                    critical=False,
                )
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .add_extension(
                    x509.KeyUsage(
                        digital_signature=True,
                        content_commitment=False,
                        key_encipherment=False,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=True,
                        crl_sign=True,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
            )
        elif type == "subca":
            ski_ext = issuer_cert.crt.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
            builder = (
                builder.add_extension(
                    x509.SubjectKeyIdentifier.from_public_key(self.pub),
                    critical=False,
                )
                .add_extension(
                    x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(ski_ext.value),
                    critical=False,
                )
                .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
                .add_extension(
                    x509.KeyUsage(
                        digital_signature=True,
                        content_commitment=False,
                        key_encipherment=False,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=True,
                        crl_sign=True,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
            )
        elif type == "server":
            ski_ext = issuer_cert.crt.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
            builder = (
                builder.add_extension(
                    x509.SubjectKeyIdentifier.from_public_key(self.pub),
                    critical=False,
                )
                .add_extension(
                    x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(ski_ext.value),
                    critical=False,
                )
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .add_extension(
                    x509.KeyUsage(
                        digital_signature=True,
                        content_commitment=False,
                        key_encipherment=True,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=False,
                        crl_sign=False,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
            )
            builder = builder.add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
        elif type == "client":
            builder = (
                builder.add_extension(
                    x509.SubjectKeyIdentifier.from_public_key(self.pub),
                    critical=False,
                )
                .add_extension(
                    x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                        issuer_cert.crt.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
                    ),
                    critical=False,
                )
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .add_extension(
                    x509.KeyUsage(
                        digital_signature=True,
                        content_commitment=True,
                        key_encipherment=True,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=False,
                        crl_sign=False,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
            )
            builder = builder.add_extension(
                x509.ExtendedKeyUsage(
                    [x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH, x509.oid.ExtendedKeyUsageOID.EMAIL_PROTECTION]
                ),
                critical=False,
            )
        else:
            raise ValueError(f"Unable to handle {type=}")
        return builder.sign(signing_pri_key, hashes.SHA256(), default_backend())

    def _x509_name(self, cn_name, org_name=None):
        name = [x509.NameAttribute(NameOID.COMMON_NAME, cn_name)]
        if org_name is not None:
            name.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name))
        return x509.Name(name)
