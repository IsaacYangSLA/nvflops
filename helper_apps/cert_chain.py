from nvflops.utils.cert_utils import SimpleCert


def write(filename: str, sc: SimpleCert):
    cert_name = filename + ".cert.pem"
    key_name = filename + ".key.pem"
    sc.serialize()
    with open(f"certs/{cert_name}", "wb") as f:
        f.write(sc.s_crt)
    with open(f"certs/{key_name}", "wb") as f:
        f.write(sc.s_prv)


rootCA = SimpleCert("ca")
rootCA.create_cert(type="root")
write("ca", rootCA)

tracker = SimpleCert("small-ubuntu-20-04")
tracker.set_issuer_simple_cert(rootCA)
tracker.create_cert(type="server")
write("nginx", tracker)

subca1 = SimpleCert("subca1")
subca1.set_issuer_simple_cert(rootCA)
subca1.create_cert(type="subca")
write("subca1", subca1)

subca2 = SimpleCert("subca2")
subca2.set_issuer_simple_cert(rootCA)
subca2.create_cert(type="subca")
write("subca2", subca2)

client1 = SimpleCert("client1")
client1.set_issuer_simple_cert(subca1)
client1.create_cert(type="client")
fp = client1.sha1_fingerprint.hex()
print(f"client1 fingerprint: {fp}")
write("client1", client1)

client2 = SimpleCert("client2")
client2.set_issuer_simple_cert(subca2)
client2.create_cert(type="client")
write("client2", client2)

filenames = ["certs/subca1.cert.pem", "certs/subca2.cert.pem", "certs/ca.cert.pem"]

with open("certs/ca-chain.cert.pem", "wb") as out_f:
    for f in filenames:
        with open(f, "rb") as in_f:
            out_f.write(in_f.read())
