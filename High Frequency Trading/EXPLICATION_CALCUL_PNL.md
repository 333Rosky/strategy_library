# 📊 Explication du Calcul de PnL - Market Making

## 🎯 Objectif

Calculer correctement le PnL d'une stratégie de market-making, en décomposant :
1. **PnL directionnel** : gains/pertes dus aux mouvements du marché
2. **Edge capture** : gains dus au fait d'acheter au bid et vendre à l'ask

---

## 💡 Principe Fondamental

En market-making, on gagne de l'argent en capturant le spread bid-ask :
- On achète au **bid** (moins cher que le mid)
- On vend à l'**ask** (plus cher que le mid)

**L'edge n'est PAS un bonus magique**, c'est simplement la conséquence d'acheter/vendre à de meilleurs prix que le mid.

---

## 📐 Formules

### 1. PnL Directionnel (incrémental)

À chaque période, si on a une position ouverte :

```python
pnl_directional[t] = position[t-1] × log(mid[t] / mid[t-1])
```

**Exemple:**
- Position : Long (+1)
- Mid passe de 100 à 101
- PnL : 1 × log(101/100) = 0.995% ≈ 1%

### 2. Edge Capture (lors des exécutions)

Lors d'un trade (changement de position) :

```python
# Nombre de transitions
n_transitions = abs(signal_new - signal_old)
# 1 si ouverture ou fermeture seule
# 2 si reverse (long → short ou vice-versa)

# Edge brut = delta par transition
edge_gross = n_transitions × delta

# Edge net = edge brut - adverse selection (si fermeture)
if fermeture:
    edge_net = edge_gross - adverse_selection
else:
    edge_net = edge_gross
```

**Exemple 1 : Ouverture long**
- Signal : 0 → +1
- Transitions : 1
- Edge : +2 bps (on achète au bid au lieu du mid)
- Adverse selection : 0 (pas de fermeture)
- **Edge net : +2 bps**

**Exemple 2 : Fermeture long**
- Signal : +1 → 0
- Transitions : 1
- Edge : +2 bps (on vend à l'ask au lieu du mid)
- Adverse selection : -0.95 bps
- **Edge net : +1.05 bps**

**Exemple 3 : Reverse (long → short)**
- Signal : +1 → -1
- Transitions : 2
- Edge : +4 bps (ferme long à l'ask + ouvre short à l'ask)
- Adverse selection : -0.95 bps
- **Edge net : +3.05 bps**

### 3. PnL Total

```python
pnl_total[t] = pnl_directional[t] + edge_capture[t]
```

---

## ⚠️ Pièges à Éviter

### ❌ Piège 1 : Double comptage du PnL directionnel

**FAUX :**
```python
# Pendant la position
for t in range(entry, exit):
    pnl += position × market_return[t]

# À la fermeture
pnl += position × log(exit_price / entry_price)  # ❌ On recompte tout !
```

**CORRECT :**
```python
# Seulement incrémental
for t in range(entry, exit+1):
    pnl += position × log(price[t] / price[t-1])
```

### ❌ Piège 2 : Edge comme bonus séparé

**FAUX :**
```python
# À chaque période
pnl = position × market_return + edge_constant  # ❌
```

L'edge n'est pas un bonus constant ! C'est capturé uniquement lors des exécutions.

**CORRECT :**
```python
# Seulement lors des trades
if filled[t]:
    pnl += edge_capture
```

### ❌ Piège 3 : Oublier l'adverse selection

**FAUX :**
```python
edge = 2 × delta  # ❌ Trop optimiste
```

**CORRECT :**
```python
# Sur un round-trip complet
edge = 2 × delta - adverse_selection
```

---

## 📊 Exemple Complet

### Scénario

```
t=0: Flat, Mid=100
t=1: Ouvre Long, Mid=100
t=2: Position Long, Mid=101
t=3: Position Long, Mid=102
t=4: Ferme (Flat), Mid=103
```

### Calcul Détaillé

#### t=1 : Ouverture Long
- Signal : 0 → +1
- PnL directionnel : 0 (pas encore de mouvement sur la position)
- Edge capture : +2 bps (achète au bid à 99.998 vs mid=100)
- **PnL[1] : +0.02%**

#### t=2 : Position Long
- Position : +1
- Mid : 100 → 101
- PnL directionnel : +1 × log(101/100) = +0.995%
- Edge capture : 0 (pas de trade)
- **PnL[2] : +0.995%**

#### t=3 : Position Long
- Position : +1
- Mid : 101 → 102
- PnL directionnel : +1 × log(102/101) = +0.985%
- Edge capture : 0
- **PnL[3] : +0.985%**

#### t=4 : Fermeture
- Signal : +1 → 0
- Mid : 102 → 103
- PnL directionnel : +1 × log(103/102) = +0.975%
- Edge capture : +2 bps - 0.95 bps = +1.05 bps = +0.0105%
- **PnL[4] : +0.986%**

### Total
```
PnL directionnel : 0 + 0.995 + 0.985 + 0.975 = +2.955%
Edge capture     : 0.02 + 0 + 0 + 0.0105 = +0.0305%
Total            : +2.986%
```

**Vérification alternative :**
```
Prix d'achat : 99.998 (bid à t=1)
Prix de vente : 103.002 (ask à t=4)
PnL = log(103.002 / 99.998) = +2.986% ✓
```

---

## 🔍 Diagnostic d'Erreurs

### Comment détecter un double comptage ?

1. **Comparer edge total vs théorique**
   ```python
   edge_per_fill = total_edge_bps / n_fills
   edge_theoretical = 2 × delta - adverse_selection
   
   if abs(edge_per_fill - edge_theoretical) > 1 bps:
       print("⚠️  Possible erreur de calcul!")
   ```

2. **Décomposer le PnL**
   ```python
   perf_directional = exp(sum(pnl_directional)) - 1
   perf_edge = exp(sum(edge_capture)) - 1
   perf_total = exp(sum(pnl_total)) - 1
   
   # Vérifier la cohérence
   if abs(perf_total - (perf_directional + perf_edge)) > 1%:
       print("⚠️  Incohérence dans la décomposition!")
   ```

3. **Tester avec signal constant**
   ```python
   # Si signal = +1 toujours (buy & hold)
   # Alors edge_capture devrait être presque 0
   # Et perf_total ≈ perf_directional
   ```

---

## 🎯 Métriques Importantes

Pour évaluer la qualité d'une stratégie de market-making :

### Performance
- **Return total** : Performance globale
- **Return directionnel** : Dû au signal/timing
- **Return edge** : Dû au spread capture

### Risque
- **Sharpe ratio** : Return / Volatilité
- **Maximum Drawdown** : Perte maximale
- **Win Rate** : % de trades gagnants

### Exécution
- **Fill Rate** : % d'ordres exécutés
- **Avg Fill Time** : Temps moyen pour être fill
- **Inventory Turnover** : Nombre de round-trips

### Coûts
- **Adverse Selection** : Coût du pick-off
- **Spread Cost** : Coût effectif du spread
- **Opportunity Cost** : Trades manqués

---

## 📚 Références

### Market-Making Académique
1. **Avellaneda & Stoikov (2008)**
   - "High-frequency trading in a limit order book"
   - Modèle classique d'optimal market-making

2. **Cartea, Jaimungal & Penalva (2015)**
   - "Algorithmic and High-Frequency Trading"
   - Référence complète sur le HFT

3. **Guéant, Lehalle & Fernandez-Tapia (2013)**
   - "Dealing with the inventory risk"
   - Gestion du risque d'inventory

### Implémentation Pratique
- Vérifier que le PnL est cohérent avec les prix d'entrée/sortie réels
- Toujours décomposer : directionnel vs edge vs coûts
- Valider sur des scénarios simples avant de tester en réel

---

## ✅ Checklist de Validation

Avant de mettre en production une stratégie de market-making :

- [ ] Le PnL directionnel est calculé incrémentalement
- [ ] L'edge est capturé uniquement lors des exécutions
- [ ] L'adverse selection est correctement déduite
- [ ] Les fees sont incluses
- [ ] Le slippage est modélisé
- [ ] L'inventory risk est géré
- [ ] Les tests sont faits sur plusieurs périodes
- [ ] La performance est décomposée (directionnel vs edge)
- [ ] Le code est testé sur des cas simples (buy&hold, etc.)
- [ ] Les métriques de risque sont calculées (Sharpe, DD, etc.)

---

**Date:** 11 décembre 2025  
**Version:** 2.0 (Corrigée)

