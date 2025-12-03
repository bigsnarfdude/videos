# Experiment 02: Neshveyev - Cartan Subproduct Systems (LaTeX Only)

## Video Details
- **Source**: https://videos.birs.ca/2025/25w5374/202512030901-Neshveyev.mp4
- **Size**: 74.9 MB
- **Model**: Gemini 3 Pro Preview
- **Date**: 2025-12-03
- **Prompt Focus**: Visual LaTeX extraction

## Results

### Metadata
- **Speaker**: Sergey Neshveyev
- **Title**: Cartan subproduct systems
- **Institution**: University of Oslo
- **Workshop**: 25w5374
- **Field**: Operator Algebras, Quantum Groups, Functional Analysis

### LaTeX Equations Extracted

**Slide 1: Definition**
```latex
$H = (H_n)_{n \ge 0}$
$H_0 = \mathbb{C}$
$H_{n+m} \subseteq H_n \otimes H_m$
$H_n = I_n^\perp \subseteq (\mathbb{C}^N)^{\otimes n}$
```

**Slide 2: Fock Space**
```latex
$f_n: H_1^{\otimes n} \to H_n$ (projection)
$\mathcal{F}_H = \bigoplus_{n=0}^\infty H_n$ (Fock space)
$S_{\xi}\zeta = f_{n+1}(\xi \otimes \zeta)$
$\sum_{i=1}^N S_i S_i^* = 1 - e_0$
```

**Slide 3: Algebras**
```latex
$\mathcal{T}_H = C^*(S_1, \dots, S_N)$ (Toeplitz algebra)
$\mathcal{O}_H = \mathcal{T}_H / \mathcal{K}(\mathcal{F}_H)$ (Cuntz-Pimsner algebra)
$p(S_1, \dots, S_N) = 0 \quad \forall p \in I$
```

**Slide 6: Temperley-Lieb**
```latex
$I = \langle X_1 X_2 - q X_2 X_1 \rangle$
$f_{n+1} = 1 \otimes f_n - \frac{[n]_q}{[n+1]_q} (1 \otimes f_n)(\dots)(1 \otimes f_n)$
```

**Slide 7: Cartan Component**
```latex
$V_{\lambda+\mu} \hookrightarrow V_\lambda \otimes V_\mu$
```

**Slide 9: Conjecture**
```latex
$\| P_{\lambda, \mu} - 1 \otimes p_\mu \|_\infty \to 0$
```

**Slide 11: Main Theorem**
```latex
$\mathcal{O}_{\lambda, q} \cong C(G_q^{\lambda} \backslash G_q)$
```

### Definitions & Theorems Extracted

**Definition (Subproduct System):** A standard subproduct system is a collection $H=(H_n)_{n \geq 0}$ such that $H_0 = \mathbb{C}$ and $H_{n+m} \subseteq H_n \otimes H_m$ isometrically.

**Arveson-Douglas Conjecture:** If ideal $I$ contains all commutators $[X_i, X_j]$, then $\mathcal{O}_H$ is commutative.

**Main Theorem:** For $q > 1$, the Cuntz-Pimsner algebra $\mathcal{O}_{\lambda, q}$ is isomorphic to $C(G_q^{\lambda} \backslash G_q)$.

### Timestamped Visual Content
- [00:04] Definition of subproduct systems
- [01:21] Fock space construction
- [03:28] Toeplitz and Cuntz-Pimsner algebras
- [06:13] Arveson's symmetric systems
- [10:54] Temperley-Lieb systems
- [14:04] Cartan component construction
- [18:42] Projection conjecture
- [24:48] Main theorem statement
- [28:30] Continuous field theorem

## Performance
- Upload: 32.1s
- Analysis: 83.0s
- **Total: ~115s (~2 min)**

## Notes
- Excellent LaTeX extraction from slides
- Captured handwritten notation correctly
- 13 timestamped visual entries
- Perfect for equation search use case
