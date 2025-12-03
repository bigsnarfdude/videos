# Experiment 04: Peter Sin - Quantum Walks on Cayley Graphs

## Video Details
- **Source**: https://videos.birs.ca/2025/25w5432/202510131332-Sin.mp4
- **Size**: 104.3 MB
- **Model**: Gemini 3 Pro Preview
- **Date**: 2025-12-03

## Results

### Metadata
- **Speaker**: Peter Sin
- **Title**: Uniform mixing of continuous-time quantum walks on oriented Cayley graphs
- **Institution**: University of Florida
- **Workshop**: 25w5432
- **Field**: Algebraic Graph Theory, Quantum Information Theory

## TRANSCRIPT HIGHLIGHTS

### [00:00-00:39] Introduction
> "We start with a Cayley graph on a group $G$ with a connecting set $C$. So that just means that you have a vertex for every group element $g$ in $G$. And this group element will be connected to $cg$. And we want it to be an oriented Cayley graph. So this means that $C$ intersects the inverse set of $C$ emptily."

### [04:59-05:50] Definition of Uniform Mixing
> "And then uniform mixing... the walk has uniform mixing (UM) at time $\tau$ if the absolute value of the entries of $U(\tau)_{ij}$ are all the same. So that would have to be $1/\sqrt{|G|}$ for all $i, j$."

### [09:38-11:19] Suzuki 2-Groups
> "These are called Suzuki 2-groups. They were first studied by Higman in around 1960. And certain ones of them arise as the Sylow 2-subgroups of these simple groups called the Suzuki groups... there are $2(2^n - 1)$ conjugacy classes of elements of order 4... no element of order 4 is conjugate to its inverse."

### [12:39-13:20] Main Theorem
> "And then the theorem is that this Cayley graph $Cay(G, C)$ has uniform mixing at $\tau = \pi/2^n$."

### [29:04-30:03] Computational Results
> "For order 64, 267 groups, 3560 difference sets with $C \cap C^{-1} = \emptyset$, 68 non-isomorphic graphs, and they all have uniform mixing. In fact, they seem to all be cospectral."

---

## VISUAL LATEX (30+ equations)

### Basic Definitions
```latex
$$ Cay(G, C) $$
$$ C \cap C^{-1} = \emptyset $$
$$ Y = \sum_{y \in Y} y \in \mathbb{C}G $$
$$ \tilde{Y} = \text{regular representation matrix} $$
```

### Skew Adjacency Matrix
```latex
$$ S = \tilde{C} - \tilde{C}^t \quad (\text{skew adjacency matrix}) $$
$$ A = \tilde{C} + \tilde{C}^t \quad (\text{adjacency matrix}) $$
```

### Quantum Walk
```latex
$$ H_{|_{1exc}} = iS $$
$$ U(t) = e^{-it H} = e^{tS} $$
```

### Uniform Mixing Condition
```latex
$$ |U(\tau)_{ij}| = \frac{1}{\sqrt{|G|}} $$
$$ \sqrt{|G|} e^{\tau S} = H $$
$$ HH^t = |G|I $$
```

### Suzuki 2-Group Matrix (EXTRACTED!)
```latex
$$ G = A(n, \theta), \quad n = 2m+1 $$
$$ \begin{pmatrix} 1 & a & b \\ 0 & 1 & a^\theta \\ 0 & 0 & 1 \end{pmatrix}, \quad a, b \in \mathbb{F}_{2^n} $$
```

### Main Theorem
```latex
$$ Cay(G, C) \text{ has UM at } \tau = \frac{\pi}{2^n} $$
```

### Difference Set Equation
```latex
$$ \tilde{C}\tilde{C}^t = kI + (k - \lambda)J $$
```

### Computational Results
```latex
$$ S(S^2 + 16I) = 0 \quad \text{(order 64 graphs)} $$
```

---

## DEFINITIONS & THEOREMS

**Oriented Cayley Graph:** A Cayley graph $Cay(G, C)$ is oriented if $C \cap C^{-1} = \emptyset$.

**Skew Adjacency Matrix:** $S = \tilde{C} - \tilde{C}^t$

**Continuous-time Quantum Walk:** Transition matrices $U(t) = e^{tS}$

**Uniform Mixing (UM):** $|U(\tau)_{u,v}| = \frac{1}{\sqrt{|G|}}$ for all $u, v$

**Theorem (Sin):** For Suzuki 2-group $G = A(n, \theta)$ with connection set $C$ formed by union of $2^n-1$ conjugacy classes of order 4 elements with $C \cap C^{-1} = \emptyset$, the graph $Cay(G, C)$ has UM at $\tau = \frac{\pi}{2^n}$.

**Difference Set:** $C \subseteq G$ is a $(v, k, \lambda)$-difference set if $CC^{-1} = k \cdot 1 + \lambda(G-1)$

---

## SUMMARY

Peter Sin presents research on **continuous-time quantum walks** on oriented Cayley graphs, focusing on conditions for **uniform mixing** - when the quantum walk reaches equal probability at all vertices.

The main theoretical result concerns **Suzuki 2-groups** $A(n, \theta)$. For specific connection sets formed from conjugacy classes of order 4 elements, these graphs achieve uniform mixing at time $\tau = \pi/2^n$.

Computational experiments using **GAP** reveal:
- Order 16: UM found in $C_4 \times C_4$ and $C_4 \rtimes C_4$
- Order 36: No UM despite suitable difference sets
- Order 64: **68 non-isomorphic graphs** with UM, all apparently cospectral

---

## Performance
- Upload: 47.5s
- Analysis: 110.0s
- **Total: 157.5s (~2.6 min)**

## Notes
- Excellent extraction of MATRIX NOTATION (Suzuki 2-group matrix)
- Captured computational results (order 64: 267 groups, 3560 diff sets, 68 graphs)
- Working group format - informal discussion captured well
- Rich LaTeX extraction (30+ equations)
