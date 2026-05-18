---
sidebar_position: 1
title: "Overview of Encryption"
---

# Overview of Encryption

**Cryptography** is the practice and study of securing information from unauthorized access. To understand encryption, we must first distinguish it from **encoding**:

- **Encoding:** A method that changes data into a different format for compatibility or integrity (e.g., Base64). It is **not** for security; anyone can reverse it.    
- **Decoding:** The reverse process of returning transformed data to its original format.

**Encryption** is a process that uses mathematical algorithms so that (ideally) only authorized entities can access the original information.

### Core Terminology

- **Plaintext:** The original, readable information.
- **Ciphertext:** The scrambled text obtained after the encryption process.
- **Decryption:** The inverse process that uses the **ciphertext** and a **secret key** to return the **plaintext**.

Encryption is not a modern invention; it has been used for centuries in military and government communications. It requires an **algorithm** (the invertible process) and a **secret key** (the variable that makes the output unique). The goal is to maintain **confidentiality** over insecure channels.

## Encryption Types

There are two primary types of encryption: symmetric and asymmetric.

### Symmetric Encryption

This is the oldest method. It uses the **same key** for both encryption and decryption.

- **Pros:** Generally fast and highly efficient for large amounts of data.
- **Cons:** The key must be shared securely. If the key is intercepted or compromised, all security is lost.
- **Common Algorithms:** AES and DES.
- **Usage:** File encryption, VPNs, and secure storage systems.

[Learn more about symmetric encryption](https://www.ibm.com/think/topics/symmetric-encryption)

### Asymmetric Encryption (Public-Key Cryptography)

This modern approach involves a **key pair**: a **public key** and a **private (secret) key**. These keys are mathematically linked but cannot be easily derived from one another.

- **How it works:** It can be used in two directions:
    1. **Encryption:** Anyone can use your _public key_ to encrypt a message, but only your _private key_ can decrypt it.
    2. **Digital Signatures:** You use your _private key_ to "sign" a document, and others use your _public key_ to verify that it truly came from you and hasn't been altered.
    
- **Pros:** Solves the primary "key distribution" problem of symmetric encryption.
- **Cons:** Slower and more resource-intensive. If the **private key is stolen**, the attacker can impersonate the owner or decrypt all private data. If it is lost, the data is permanently inaccessible.
- **Common Algorithms:** RSA and DSA.
- **Usage:** SSL/TLS (HTTPS), digital signatures, and secure email (PGP).

[Learn more about asymmetric encryption](https://www.ibm.com/think/topics/asymmetric-encryption)

### The Key Exchange Problem

In practice, both types of encryption are used together. **Asymmetric encryption** is used to solve the key exchange problem, and then the agreed **symmetric key** is used for the actual data transfer. This hybrid approach is how **HTTPS** works, using the security of public keys to "hand off" a faster symmetric key.

However, this creates a "chicken and egg" paradox: **How do two people who have never met agree on a secret key over an insecure connection without an eavesdropper seeing it?** If you simply send the symmetric key over the internet, the solution (encryption) suffers from the very same issue it's trying to solve: interception.

### Diffie-Hellman Key Exchange

The **Diffie-Hellman algorithm** is a brilliant solution to this paradox. It allows two parties to establish a "shared secret" over an unsecure channel.

1. Both parties choose their own **private value** (which they never share).
2. They agree on a **public value**.
3. Each party combines their private value with the public value to create a **result**, which they then send to each other.
4. Finally, they each combine the other person's result with their own original private value.

Because of the underlying math, both parties arrive at the **exact same final number**. An eavesdropper who sees the public exchanges cannot easily reverse the math to find the secret keys. This final number is then used as the **symmetric key** for a fast, secure conversation.

## Key Properties

Beyond the type of algorithm you choose, the security of your information depends on how you manage the keys themselves.

#### 1. Key Length & Brute Force
The security of a key is often tied to its length, measured in bits. A **brute force attack** is when an attacker uses a computer to try every possible combination until they find the right one, like trying every possible code on a suitcase lock. The longer the key, the more combinations there are. For instance, adding just one bit doubles the number of possible combinations, making it exponentially harder and more time-consuming for a computer to "guess" the key.

#### 2. Key Rotation
Even if a key hasn't been stolen, it is best practice to replace it periodically. This is called **key rotation**. By changing keys regularly, you limit the amount of data encrypted with any single key. If a key is eventually compromised, only the small "slice" of data associated with that specific key is at risk, rather than your entire history of communications.

#### 3. Key Leakage & "Harvest Now, Decrypt Later"
The danger of a stolen key isn't just about future messages; it's retrospective. If an attacker has been intercepting and storing your encrypted traffic for months, and then they finally steal your key, they can go back and decrypt every single thing they previously collected. This strategy is known as **"harvest now, decrypt later."** It is a major concern today, especially as we look toward future threats like quantum computing that might break current encryption.

#### 4. Key Storage
An algorithm can be mathematically perfect, but it won't matter if the key is left "under the doormat." A key is only as safe as the environment where it lives. In professional settings, keys are often stored in specialized hardware like **HSMs (Hardware Security Modules)** or secure "vaults" to ensure they cannot be easily exported or copied by unauthorized users.