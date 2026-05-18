---
sidebar_position: 2
title: "How Keys Are Distributed Today"
---

# How Keys Are Distributed Today

Digital communication happens across untrusted networks. Without strong mechanisms, parties cannot reliably verify who they are talking to, confirm that messages haven't been altered in transit, or keep data confidential from eavesdroppers. PKI and TLS are the systems the world built to solve this.

## What PKI Is

**Public Key Infrastructure (PKI)** is the framework of technologies, policies, and procedures that makes secure communication on the internet possible. Its core job is simple: **tie a public key to a real-world identity** in a way that others can verify.

It does this through **certificates** — documents that say _"this public key belongs to google.com"_ — signed by an authority that your browser already trusts.

### The Trust Hierarchy

The system is built as a chain of trust:

- **Root CA (trust anchor):** A Certificate Authority whose public key comes pre-installed in your browser or operating system. You trust your browser, your browser trusts the root CA. Root keys are extremely sensitive. they are kept offline or in Hardware Security Modules (HSMs) and used as rarely as possible.
- **Intermediate CA:** Issued and signed by a root CA. These perform the day-to-day work of signing certificates, limiting how often the root key needs to be used.
- **End-entity certificate:** The certificate your browser actually receives when connecting to a server. It represents google.com (or whoever you're connecting to), contains their public key, and is signed by an intermediate CA.

The result is a **chain**: your browser trusts the root → the root vouches for the intermediate → the intermediate vouches for google.com. This is called the **certificate chain**.

### How Validation Works

When your browser receives a certificate, it does the following:

1. **Builds the chain** from the server's certificate up to a root CA it already trusts.
2. **Verifies each signature** in the chain: each certificate is signed by the one above it, all the way to the root.
3. **Checks expiry dates**: every certificate in the chain must be currently valid.
4. **Confirms the identity**: the certificate must match the domain you're connecting to (e.g., `google.com`).
5. **Checks revocation** the certificate must not have been revoked by the CA (in case the private key was compromised).

If any of these checks fail, the browser stops and warns you. This is that _"your connection is not private"_ screen.

Once all checks pass, the browser has one important guarantee: **the public key in the certificate genuinely belongs to the server it claims to be.** A trusted authority said so, and the math backs it up.

## TLS: Putting It Together

PKI tells you _who_ you're talking to. **TLS (Transport Layer Security)** is the protocol that uses that identity to establish a secure, encrypted channel.

Here is what happens after your browser validates the certificate:

### 1. Agreeing on Parameters

The client and server negotiate which TLS version and **cipher suite** to use, the specific combination of algorithms for key exchange, encryption, and integrity checking.

### 2. Key Exchange (Diffie-Hellman)

Both sides agree on a public common value. Each generates a private secret, combines it with the common value, and sends the result to the other. Thanks to the math of Diffie-Hellman, both sides arrive at the same final number — the **shared secret** — without ever transmitting it directly. The server signs its DH value with its private key (proven by the certificate) so the client can confirm it's genuinely talking to google.com and not an impersonator.

To ensure **forward secrecy**, both sides also contribute a random value (a **nonce**) that is unique to this session. This means the final symmetric key is bound to this connection only. Even if an attacker records the traffic today and steals the server's private key years later, they cannot reconstruct this session's key.

### 3. Symmetric Encryption Begins

The shared secret is used to derive a **symmetric key**. From this point, all data is encrypted with a fast symmetric algorithm (typically AES). PKI and Diffie-Hellman solved the key distribution problem, now the fast, efficient encryption takes over.

### 4. Integrity Verification

Before the handshake is considered complete, both sides exchange a **MAC (Message Authentication Code)**, essentially a hash of the entire handshake conversation. If both sides compute the same value, it confirms that no one tampered with the negotiation. Only then does the secure session begin.

## The Assumption Underneath Everything

This system — PKI, CAs, TLS — works extraordinarily well, and secures virtually all internet traffic today. But it rests on two core assumptions:

**First:** Certificate Authorities are honest, secure, and issue certificates only after proper validation. This has failed before. In 2011, a CA called DigiNotar was compromised and issued fraudulent certificates for google.com, allowing attackers to intercept users' traffic. DigiNotar was removed from all browser trust stores and went bankrupt shortly after.

**Second:** The underlying math is hard enough to be unbreakable in practice. RSA and Diffie-Hellman rely on mathematical problems — like factoring very large numbers — that would take classical computers longer than the age of the universe to solve.

That second assumption is what the next section will challenge.