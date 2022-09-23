from nvflops.utils.cert_utils import SimpleCert

ca = SimpleCert("study1", ca=True)
ca.create_cert()
ca.serialize()
sc = SimpleCert("party1")
sc.set_issuer_simple_cert(ca)
sc.create_cert()
sc.serialize()
with open("sc.crt", "wt") as f:
    f.write(sc.s_crt.decode('utf-8'))

with open("sc.prv", "wt") as f:
    f.write(sc.s_prv.decode('utf-8'))
