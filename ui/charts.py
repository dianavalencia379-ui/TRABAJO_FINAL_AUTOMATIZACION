"""Gráficos personalizados para el dashboard, construidos con matplotlib.

Se centralizan aquí (en vez de inline en cada pestaña) porque son figuras
reutilizables con lógica de diseño propia (curvas, anotaciones, colores),
separarlas mejora la legibilidad de tab_overview.py y permite reutilizarlas
desde otras pestañas si hace falta más adelante.

Se eligió matplotlib en vez de Plotly porque Plotly todavía no está en
requirements.txt (esa integración corresponde al RACI de José) y estas dos
figuras no requieren interactividad -- son estáticas por diseño.
"""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from scipy.interpolate import PchipInterpolator


def build_waterfall_figure(
    *,
    saldo_inicial: float,
    aportes: float,
    rendimientos: float,
    retiros: float,
    gastos: float,
    start_label: str,
    end_label: str,
) -> Figure:
    """Construye la figura 'Movimiento del Periodo' (diagrama esquemático).

    Saldo inicial + aportes + rendimientos − retiros − gastos = saldo final.

    IMPORTANTE: la curva NO está a escala con los montos reales -- es un
    diagrama de referencia con una forma fija (sube para aportes+
    rendimientos, baja para retiros+gastos, se nivela al final), igual que
    la imagen de referencia del equipo. Los montos reales se muestran como
    texto en cada etiqueta; la altura de la curva es solo ilustrativa del
    tipo de movimiento (entrada vs. salida), no de su magnitud.
    """
    saldo_final = saldo_inicial + aportes + rendimientos - retiros - gastos

    # Forma fija del diagrama (6 puntos de referencia, sin relación con
    # los montos reales): plano -> sube -> pico -> valle -> se nivela -> plano
    x_points = np.array([0, 1, 2, 3, 4, 5])
    y_points = np.array([0.0, 0.55, 1.0, -1.0, 0.0, 0.0])

    x_smooth = np.linspace(0, 5, 360)
    interpolator = PchipInterpolator(x_points, y_points)
    y_smooth = interpolator(x_smooth)

    fig = Figure(figsize=(11.5, 4.6))
    ax = fig.add_subplot(111)
    ax.plot(x_smooth, y_smooth, color="#9aa5b1", linewidth=2.6, zorder=1)

    ax.scatter([0], [0.0], s=170, facecolors="white", edgecolors="#1d4ed8", linewidths=2.6, zorder=3)
    ax.scatter([5], [0.0], s=170, facecolors="white", edgecolors="#1d4ed8", linewidths=2.6, zorder=3)
    ax.scatter([2], [1.0], s=130, color="#16a34a", zorder=3)
    ax.scatter([3], [-1.0], s=130, color="#dc2626", zorder=3)
    ax.scatter([4], [0.0], s=110, color="#9ca3af", zorder=3)

    def _money(value: float) -> str:
        """Formatea evitando el caso '-$0' (Python conserva el signo de -0.0)."""
        normalized = 0.0 if value == 0 else value
        return f"${normalized:,.0f}" if normalized == 0 else f"${normalized:+,.0f}"

    label_kwargs = dict(ha="center", fontsize=11, color="#374151")
    ax.annotate(f"Aportes\n{_money(aportes)}", xy=(1, 0.7), **label_kwargs)
    ax.annotate(f"Rendimientos\n{_money(rendimientos)}", xy=(2.6, 1.32), **label_kwargs)
    ax.annotate(f"Retiros\n{_money(-retiros)}", xy=(2.4, -1.32), **label_kwargs)
    ax.annotate(f"Gastos y comisiones\n{_money(-gastos)}", xy=(4, -0.62), **label_kwargs)

    ax.annotate(
        f"Saldo inicial\n${saldo_inicial:,.0f}\n{start_label}",
        xy=(0, 0), xytext=(0, -0.55),
        ha="center", fontsize=11.5, color="#1d4ed8", fontweight="bold",
    )
    ax.annotate(
        f"Saldo final\n${saldo_final:,.0f}\n{end_label}",
        xy=(5, 0), xytext=(5, 0.55),
        ha="center", fontsize=11.5, color="#1d4ed8", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", fc="#fef9c3", ec="#eab308", lw=1.2),
    )

    ax.set_xlim(-0.7, 5.7)
    ax.set_ylim(-1.9, 1.9)
    ax.axis("off")
    fig.tight_layout()
    return fig


def build_donut_figure(*, labels: list[str], values: list[float], amounts: list[float] | None = None) -> Figure:
    """Construye un gráfico de anillo en MEDIO círculo (estilo gauge),
    con cada porción etiquetada directamente (ticker, monto y %), sin
    leyenda externa -- así se gana espacio horizontal.

    Técnica: se agrega una porción invisible igual a la suma de los datos
    reales, de modo que estos ocupen exactamente la mitad del círculo;
    luego se recorta la figura para mostrar solo esa mitad superior.

    Las etiquetas se posicionan a mano (no con el parámetro labels= de
    ax.pie) porque con varias porciones pequeñas juntas (ej. dos activos
    con peso similar) el posicionamiento automático las hace solaparse;
    alternar la distancia (cerca/lejos) con líneas guía evita ese choque.
    """
    fig = Figure(figsize=(8.0, 4.6))
    ax = fig.add_subplot(111)

    if not values or sum(values) <= 0:
        ax.text(0.5, 0.5, "Sin datos de composición", ha="center", va="center", fontsize=12, color="#6b7280")
        ax.axis("off")
        return fig

    total = sum(values)
    padded_values = list(values) + [total]
    colors = _blues(len(values)) + ["none"]

    if amounts is None:
        amounts = [None] * len(values)

    wedges, _texts = ax.pie(
        padded_values,
        colors=colors,
        startangle=180,
        counterclock=False,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
    )

    # Solo las porciones reales (se descarta la última, invisible)
    real_wedges = wedges[: len(values)]
    for index, (wedge, ticker, weight_pct, amount) in enumerate(zip(real_wedges, labels, values, amounts)):
        angle_rad = np.deg2rad((wedge.theta1 + wedge.theta2) / 2)
        x_edge, y_edge = np.cos(angle_rad), np.sin(angle_rad)

        # Distancia alternada (cerca/lejos) para que porciones angularmente
        # próximas no choquen sus etiquetas entre sí.
        label_distance = 1.45 if index % 2 == 0 else 1.72
        x_label, y_label = x_edge * label_distance, y_edge * label_distance

        amount_part = f"${amount:,.0f}\n" if amount is not None else ""
        text = f"{ticker}\n{amount_part}{weight_pct:.1f}%"

        ax.annotate(
            text,
            xy=(x_edge * 1.0, y_edge * 1.0),
            xytext=(x_label, y_label),
            ha="center", va="center", fontsize=10.5, color="#374151",
            arrowprops=dict(arrowstyle="-", color="#9ca3af", linewidth=1.0),
        )

    ax.set_aspect("equal")
    ax.set_xlim(-1.9, 1.9)
    ax.set_ylim(-0.15, 1.9)
    fig.tight_layout()
    return fig


def build_area_figure(*, dates: list[str], values: list[float]) -> Figure:
    """Construye el gráfico de evolución con relleno claro y línea oscura
    encima (estilo de la imagen de referencia del equipo), con una
    etiqueta flotante señalando el último punto (valor actual).
    """
    fig = Figure(figsize=(8.2, 4.3))
    ax = fig.add_subplot(111)

    x_positions = list(range(len(values)))
    ax.fill_between(x_positions, values, color="#bfdbfe", alpha=0.65, zorder=1)
    ax.plot(x_positions, values, color="#1d4ed8", linewidth=2.4, zorder=2)
    ax.scatter([x_positions[-1]], [values[-1]], color="#1d4ed8", s=55, zorder=3)

    last_value = values[-1]
    value_range = max(max(values) - min(values), 1.0)
    ax.annotate(
        f"{dates[-1]}\n${last_value:,.0f}",
        xy=(x_positions[-1], last_value),
        xytext=(x_positions[-1] - len(values) * 0.16, last_value + value_range * 0.18),
        fontsize=10.5, color="white", ha="center", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.5", fc="#1d4ed8", ec="none"),
    )

    tick_step = max(len(dates) // 8, 1)
    ax.set_xticks(x_positions[::tick_step])
    ax.set_xticklabels([dates[i] for i in x_positions[::tick_step]], rotation=0, fontsize=9.5, color="#6b7280")
    ax.tick_params(axis="y", labelsize=9.5, colors="#6b7280")
    for spine_name in ("top", "right", "left"):
        ax.spines[spine_name].set_visible(False)
    ax.spines["bottom"].set_color("#d1d5db")
    ax.yaxis.set_tick_params(length=0)
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
    ax.set_axisbelow(True)

    fig.tight_layout()
    return fig


def _blues(count: int) -> list[tuple[float, float, float, float]]:
    """Genera una paleta de azules degradados sin depender de pyplot global."""
    from matplotlib import colormaps

    cmap = colormaps.get_cmap("Blues")
    return [cmap(value) for value in np.linspace(0.95, 0.35, max(count, 1))]