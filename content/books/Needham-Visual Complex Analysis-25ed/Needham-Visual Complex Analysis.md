---
title: Needham-Visual Complex Analysis
topics:
  - math
  - complex
created: 2025-05-24 20:06:57
modified: 2025-05-24 20:06:57
slug: Needham-Virtual-Complex-Analysis
source: https://www.amazon.com/Visual-Complex-Analysis-25th-Anniversary-ebook/dp/B0BV2TYMHW/ref=tmm_kin_swatch_0
---
Newton's geometric calculus
# $\asymp$

- Needham, in the 25th anniversary edition (2021) of the original Oxford publication of "Visual Complex Analysis", clarifies the example he used in the original edition of Newton's third formulation of differentiation, in which Newton abandons his earlier use of symbolic manipulation to emphasize the geometric foundation and analysis.  Newton uses "ultimately equal", or, with Needham's modern symbolism, the equivalence relation symbolized by $\asymp$.
- Here is the sequence of steps that show how the desired derivative is equivalent to a sequence of geometrical ratios. The notation for "ultimately equal" shows the sequence as $\delta\theta$ goes to zero, ending with a multiplication, and the geometric identity with a Pythagorean theorem result.

$$ \frac {dT}{L d\theta}\asymp \frac {\delta T}{L \delta\theta}\asymp \frac {\delta T}{\delta s}\asymp \frac{L}{1} \implies \frac {dT}{d\theta}= L^2 = 1 + T^2
$$
## Details
- \ asymp Latex symbol

## Links/References

- [Source](https://www.amazon.com/Visual-Complex-Analysis-25th-Anniversary-ebook/dp/B0BV2TYMHW/ref=tmm_kin_swatch_0)
- Needham (1993)
- Needham-VCA (1997)
- Needham (2014)
- [[Why Machines Learn]]
- 

## Discussion of "ultimately equal"

-  Needham rebuilds Newton's use of geometric calculus, rather than Leibnizian symbolic calculus, and describes how he rewrote the new edition to emphasize this distinction.
- Needham apologizes for failing to have the courage to use the  geometric "ultimately equal" notation 25 years ago, and demonstrates it's use by rewriting a key proof using geometric calculus in the Preface. 
- In the new edition, he significantly changes the drawing of the geometry of the proof. For the first time, he shows the arc of the circle of radius L, showing how, in the "ultimately equal" process, the length of the arc from the original vertex of the triangle, to the new vertex after rotating the hypotenuse by the small amount $\delta\theta$, becomes equal to the orthogal distance. He shows this using the derivative of the complex quantity  $re^{i\theta}$, using a triangle with base 1 and vertical side T, so that T = $tan (\theta)$, and the rotation increases the length of the vertical side T by  $\delta T$
- 
- Needham uses the symbol $\asymp$  for "differential equality." This is a beautiful and intuitive notation that perfectly captures the geometric concept he's describing.

The symbol $\asymp$ (asymptotically equal) is quite fitting for Needham's geometric approach because:

1. **Visual intuition**: The curved lines suggest that the quantities are "approximately equal" in a limiting sense, rather than exactly equal at any finite scale.

2. **Differential relationship**: When he writes something like $dT \asymp L \cdot d\theta$, he's indicating that these quantities become equal in the differential limit - they differ by terms of higher order that vanish as $d\theta \to 0$.

3. **Geometric meaning**: This notation emphasizes that we're dealing with infinitesimal geometric relationships where the "error" in the equality becomes negligible compared to the quantities themselves.

This is exactly what we were discussing with the geometric proof of $\frac{dT}{d\theta} = 1 + T^2$. When Needham says the perpendicular distance is $L \cdot d\theta$, he might write:

$$\text{perpendicular distance} \asymp L \cdot d\theta$$

This captures the idea that for infinitesimal $d\theta$, the straight-line perpendicular distance and the arc length $L \cdot d\theta$ are differentially equal - they differ by terms of order $(d\theta)^2$ or higher, which vanish in the limit.

This notation beautifully embodies Needham's philosophy of making the geometric intuition behind calculus concepts visually and symbolically clear. It's a much more intuitive way to express infinitesimal relationships than the traditional $\epsilon$-$\delta$ formalism, while still being mathematically precise.