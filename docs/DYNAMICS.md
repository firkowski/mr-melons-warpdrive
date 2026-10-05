# Dynamics and CAD parameter contract

## Frames and assumptions

The fixed motor axis is world +z. At $\theta=0$ the arm points along +x. Its length is $r$. The pendulum hinge rotates about **arm-local +x**, the radial direction. The pendulum frame orientation is $R_z(\theta)R_x(\alpha)$. At $\alpha=0$ its COM is $l$ above the pivot; positive $\alpha$ initially moves its COM towards arm-local −y. Consequently, in the arm frame,
$$p_C=(r,-l\sin\alpha,l\cos\alpha).$$
The pendulum COM must lie on its local z axis. Its COM inertia is diagonal in the specified body frame: $\operatorname{diag}(I_x,I_y,I_z)$. This includes a symmetric rectangular rod, with potentially different $I_x$ and $I_y$. An asymmetric part with nonzero products of inertia or an off-axis COM requires a different model or an explicitly justified approximation.

$J_a$ is the combined arm-group inertia about the vertical motor axis, **excluding the pendulum**. It includes any rigidly attached rotating hardware; a stationary motor housing is not part of it. $J_a$ (`arm_inertia`) and $r$ (`arm_length`) are supplied in `config/reactor_params.yaml`.

No small-angle approximation is used in the supplied swing-up dynamics. Current tracking is ideal; torque is $\tau=K_{\tau,\mathrm{out}}i$. The effective output torque constant includes any chosen gearing convention. No voltage, inductance or inner-loop servo model is included.

## Equations

Let $s=\sin\alpha$, $c=\cos\alpha$, $k=mrl$, and $D=I_y+ml^2-I_z$. Then

$$
M=\begin{bmatrix}
J_a+mr^2+(I_y+ml^2)s^2+I_zc^2 & -kc\\
-kc & I_x+ml^2
\end{bmatrix},
$$

$$
h=\begin{bmatrix}2Dsc\,\dot\theta\dot\alpha+ks\,\dot\alpha^2\\-Dsc\,\dot\theta^2\end{bmatrix},
\quad g(q)=\begin{bmatrix}0\\-mgls\end{bmatrix},
\quad B=\operatorname{diag}(b_a,b_p).
$$

Solve

$$M\ddot q=\begin{bmatrix}\tau\\0\end{bmatrix}-h-g(q)-B\dot q.$$

The implementation uses the explicit two-by-two solve and integrates the four-state derivative with fixed-step RK4. Both training and ROS call `step_dynamics`; there is no duplicate physics. The sign of the off-diagonal term follows the frame definition above. Equations from a source
using a different pendulum angle direction must be transformed before comparing signs.

A useful independent check is total energy:

$$E=\tfrac12\dot q^T M\dot q+mgl\cos\alpha,\qquad
\dot E=\tau\dot\theta-b_a\dot\theta^2-b_p\dot\alpha^2.$$

With zero damping and zero current, $E$ stays constant; this is a quick way to test the integrator.

## Extracting CAD properties

The arm values are supplied; you only extract the pendulum's properties.

1. Assign the specified material density to the part.
2. Obtain the pendulum's mass, COM and inertia tensor **about its COM**, expressed in the
   pendulum axes defined above. Confirm that the products of inertia are negligible.
3. Enter the positive pivot-to-COM distance as `pendulum_com`. Enter the three COM moments directly.
4. Convert units before entering values: g → kg multiply by $10^{-3}$; mm → m multiply by $10^{-3}$;
   kg·mm² → kg·m² multiply by $10^{-6}$; g·mm² → kg·m² multiply by $10^{-9}$.

If you ever need to combine several bodies, use rotated inertia tensors and the parallel-axis theorem:

$$I_O=R I_C R^T+m\big((d^Td)\mathbf{1}-dd^T\big).$$

Do not sum arbitrary CAD-reported principal moments from different frames. The provided model already contains $ml^2$ and $mr^2$ terms; entering pendulum pivot inertia would double-count them.

## Worked example: a uniform box

This example is **not** the reactor's pendulum; use it to check your unit conversions and the meaning of each field. Consider a uniform box with local x thickness 4 mm, local y width 12 mm and local z length 140 mm, pivoting at the centre of its lower end face when upright, with density
2700 kg/m³ (aluminium). Then:

- $m=0.018144$ kg and $l=0.07$ m (pivot to COM, half the length).
- $I_x=m(0.012^2+0.14^2)/12=2.9852928\times10^{-5}$ kg·m².
- $I_y=m(0.004^2+0.14^2)/12=2.9659392\times10^{-5}$ kg·m².
- $I_z=m(0.004^2+0.012^2)/12=2.4192\times10^{-7}$ kg·m².

These are moments about the COM. The model adds $ml^2$ itself; entering $I_x+ml^2$ would count it twice.

The remaining values in `config/reactor_params.yaml` are chosen simulation values: an ideal current-controlled motor with torque constant 2.0 N·m/A and a 5 A current limit, plus small viscous damping. They are not the specification of a real servo.

Background: [Cazzolato and Prime, On the Dynamics of the Furuta Pendulum](https://digital.library.adelaide.edu.au/items/2dee399a-84e2-4990-a1e1-c191c44d3b92).
