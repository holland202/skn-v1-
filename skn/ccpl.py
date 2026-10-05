"""C-CPL docking signatures with ML-DSA-65 (FIPS 204), built (docs/PREREG_2026-09-27.md, K2).

Uses the pure-Python reference implementation `dilithium-py` (pip install dilithium-py). It is correct
but NOT constant time and NOT side-channel hardened: suitable for simulation and tests, not for an
adversarial radio link. Without the package, docking fails closed: no lock, nothing committed.

A dock record is plain JSON-serialisable data:
  {"manifest": {...}, "manifest_sha3_512": hex, "signature": hex, "public_key_sha3_256": hex}
`verify_dock(record, public_key, seen_nonces)` checks the digest, the signature, the key fingerprint and
that the nonce is new.
"""
import hashlib
import json
import os
import time

try:
    from dilithium_py.ml_dsa import ML_DSA_65
except ImportError:  # fail closed, see sign_manifest
    ML_DSA_65 = None

UNAVAILABLE = "ML-DSA-65 unavailable (pip install dilithium-py)"
NO_STORE = "no nonce store: replay cannot be checked (fail closed)"


def available():
    return ML_DSA_65 is not None


def keygen():
    """(public_key, secret_key) bytes. Raises RuntimeError if ML-DSA-65 is unavailable."""
    if ML_DSA_65 is None:
        raise RuntimeError(UNAVAILABLE)
    return ML_DSA_65.keygen()


def canonical(manifest):
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def make_manifest(node_id, target_id, pose, alignment, strain, nonce=None, t=None):
    """The fields a dock commits to. Floats are rounded to 6 places so the record is stable as JSON."""
    rnd = lambda xs: [round(float(x), 6) for x in xs]  # noqa: E731
    return {"schema": "skn.ccpl_manifest/1", "node_id": node_id, "target_id": target_id,
            "pose": rnd(pose), "alignment": rnd(alignment), "strain": rnd(strain),
            "nonce": nonce or os.urandom(16).hex(), "time": t if t is not None else time.time()}


def sign_manifest(manifest, public_key, secret_key):
    """A dock record for `manifest`. Raises RuntimeError if ML-DSA-65 is unavailable."""
    if ML_DSA_65 is None:
        raise RuntimeError(UNAVAILABLE)
    digest = hashlib.sha3_512(canonical(manifest)).digest()
    sig = ML_DSA_65.sign(secret_key, digest)
    return {"manifest": manifest, "manifest_sha3_512": digest.hex(), "signature": sig.hex(),
            "public_key_sha3_256": hashlib.sha3_256(public_key).hexdigest()}


def verify_dock(record, public_key, seen_nonces=None):
    """(ok, why). seen_nonces: a set the caller keeps; a verified nonce is added, a repeat is refused.
    Without a store the record is refused (K8), after the integrity checks so their reasons are unchanged.
    The store is in memory and kept by the caller: a fresh set per call, or a restart, forgets every nonce."""
    if ML_DSA_65 is None:
        return False, UNAVAILABLE
    try:
        manifest = record["manifest"]
        digest = hashlib.sha3_512(canonical(manifest)).digest()
        if digest.hex() != record["manifest_sha3_512"]:
            return False, "manifest does not hash to manifest_sha3_512"
        if hashlib.sha3_256(public_key).hexdigest() != record["public_key_sha3_256"]:
            return False, "record names a different public key"
        if not ML_DSA_65.verify(public_key, digest, bytes.fromhex(record["signature"])):
            return False, "signature does not verify"
        # K8 (2026-10-05): without a store the replay check cannot run, so refuse. Before K8 a missing store
        # (the default) skipped the check and accepted the same record every time (fail-open).
        if seen_nonces is None:
            return False, NO_STORE
        if manifest["nonce"] in seen_nonces:
            return False, "nonce already seen (replay)"
        seen_nonces.add(manifest["nonce"])
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed record: {type(exc).__name__}"
    return True, "ML-DSA-65 signature valid"
