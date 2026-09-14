
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from dataclasses import dataclass
from math import sin, cos, radians, sqrt, atan2, degrees


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Iceberg Trajectory Simulator",
    page_icon="🧊",
    layout="wide"
)


# ============================================================
# TITLE
# ============================================================

st.title("🧊 Iceberg Trajectory Simulator")
st.markdown(
    """
    **2D Horizontal Ocean Motion Simulator**

    This simulation calculates iceberg motion using:
    - Ocean current
    - Wind force
    - Water drag
    - Coriolis force
    - Mass and buoyancy
    - RK4 numerical integration
    """
)


# ============================================================
# ICEBERG CLASS
# ============================================================

@dataclass
class Iceberg:

    # Geometry
    length: float
    width: float
    height: float

    # Material properties
    ice_density: float
    water_density: float
    air_density: float

    # Drag coefficients
    water_drag_coefficient: float
    wind_drag_coefficient: float

    # Areas
    exposed_area: float
    underwater_area: float

    # Wind
    wind_speed: float
    wind_direction: float

    # Ocean current
    current_speed: float
    current_direction: float

    # Latitude
    latitude: float

    # Initial conditions
    x0: float
    y0: float
    vx0: float
    vy0: float

    # Simulation
    total_time: float
    dt: float

    @property
    def volume(self):
        return self.length * self.width * self.height

    @property
    def mass(self):
        return self.ice_density * self.volume

    @property
    def submerged_volume(self):
        return (
            self.ice_density
            / self.water_density
            * self.volume
        )

    @property
    def submerged_fraction(self):
        return self.submerged_volume / self.volume

    @property
    def weight(self):
        return self.mass * 9.81

    @property
    def buoyant_force(self):
        return (
            self.water_density
            * 9.81
            * self.submerged_volume
        )


# ============================================================
# VELOCITY VECTOR
# ============================================================

def velocity_vector(speed, direction_deg):

    angle = radians(direction_deg)

    return np.array([
        speed * cos(angle),
        speed * sin(angle)
    ])


# ============================================================
# FORCE CALCULATION
# ============================================================

def calculate_forces(state, iceberg):

    x, y, vx, vy = state

    m = iceberg.mass

    iceberg_velocity = np.array([vx, vy])

    # --------------------------------------------------------
    # GRAVITY
    # --------------------------------------------------------

    gravity = np.array([0.0, 0.0])

    # Vertical gravity is balanced by buoyancy
    # in this horizontal model.

    # --------------------------------------------------------
    # BUOYANCY
    # --------------------------------------------------------

    buoyancy = np.array([0.0, 0.0])

    # Vertical forces are not integrated
    # in the horizontal trajectory calculation.

    # --------------------------------------------------------
    # OCEAN CURRENT
    # --------------------------------------------------------

    current_velocity = velocity_vector(
        iceberg.current_speed,
        iceberg.current_direction
    )

    relative_water_velocity = (
        iceberg_velocity - current_velocity
    )

    relative_water_speed = np.linalg.norm(
        relative_water_velocity
    )

    # --------------------------------------------------------
    # WATER DRAG
    # --------------------------------------------------------

    if relative_water_speed > 0:

        water_drag = (
            -0.5
            * iceberg.water_density
            * iceberg.water_drag_coefficient
            * iceberg.underwater_area
            * relative_water_speed
            * relative_water_velocity
        )

    else:

        water_drag = np.zeros(2)

    # --------------------------------------------------------
    # WIND FORCE
    # --------------------------------------------------------

    wind_velocity = velocity_vector(
        iceberg.wind_speed,
        iceberg.wind_direction
    )

    relative_wind_velocity = (
        wind_velocity - iceberg_velocity
    )

    relative_wind_speed = np.linalg.norm(
        relative_wind_velocity
    )

    if relative_wind_speed > 0:

        wind_force = (
            0.5
            * iceberg.air_density
            * iceberg.wind_drag_coefficient
            * iceberg.exposed_area
            * relative_wind_speed
            * relative_wind_velocity
        )

    else:

        wind_force = np.zeros(2)

    # --------------------------------------------------------
    # CORIOLIS FORCE
    # --------------------------------------------------------

    omega = 7.2921159e-5

    latitude_rad = radians(iceberg.latitude)

    f = 2 * omega * sin(latitude_rad)

    coriolis_force = np.array([
        m * f * vy,
        -m * f * vx
    ])

    # --------------------------------------------------------
    # TOTAL HORIZONTAL FORCE
    # --------------------------------------------------------

    total_force = (
        water_drag
        + wind_force
        + coriolis_force
    )

    return total_force, {
        "gravity": gravity,
        "buoyancy": buoyancy,
        "water_drag": water_drag,
        "wind_force": wind_force,
        "coriolis_force": coriolis_force,
        "total_force": total_force
    }


# ============================================================
# DIFFERENTIAL EQUATIONS
# ============================================================

def derivatives(state, iceberg):

    x, y, vx, vy = state

    total_force, forces = calculate_forces(
        state,
        iceberg
    )

    acceleration = total_force / iceberg.mass

    return np.array([
        vx,
        vy,
        acceleration[0],
        acceleration[1]
    ])


# ============================================================
# RK4 NUMERICAL INTEGRATION
# ============================================================

def rk4_step(state, dt, iceberg):

    k1 = derivatives(
        state,
        iceberg
    )

    k2 = derivatives(
        state + 0.5 * dt * k1,
        iceberg
    )

    k3 = derivatives(
        state + 0.5 * dt * k2,
        iceberg
    )

    k4 = derivatives(
        state + dt * k3,
        iceberg
    )

    return state + (
        dt / 6.0
        * (
            k1
            + 2 * k2
            + 2 * k3
            + k4
        )
    )


# ============================================================
# SIMULATION
# ============================================================

def simulate(iceberg):

    state = np.array([
        iceberg.x0,
        iceberg.y0,
        iceberg.vx0,
        iceberg.vy0
    ], dtype=float)

    times = [0.0]

    states = [state.copy()]

    force_history = []

    t = 0.0

    while t < iceberg.total_time:

        total_force, forces = calculate_forces(
            state,
            iceberg
        )

        force_history.append(forces)

        state = rk4_step(
            state,
            iceberg.dt,
            iceberg
        )

        t += iceberg.dt

        times.append(t)
        states.append(state.copy())

    return (
        np.array(times),
        np.array(states),
        force_history
    )


# ============================================================
# SIDEBAR INPUTS
# ============================================================

st.sidebar.header("🧊 Iceberg Parameters")

# ------------------------------------------------------------
# Geometry
# ------------------------------------------------------------

st.sidebar.subheader("Geometry")

length = st.sidebar.number_input(
    "Length (m)",
    min_value=0.01,
    value=10.0,
    step=1.0
)

width = st.sidebar.number_input(
    "Width (m)",
    min_value=0.01,
    value=10.0,
    step=1.0
)

height = st.sidebar.number_input(
    "Height (m)",
    min_value=0.01,
    value=10.0,
    step=1.0
)


# ------------------------------------------------------------
# Material
# ------------------------------------------------------------

st.sidebar.subheader("Material")

ice_density = st.sidebar.number_input(
    "Ice density (kg/m³)",
    min_value=0.01,
    value=917.0,
    step=1.0
)

water_density = st.sidebar.number_input(
    "Water density (kg/m³)",
    min_value=0.01,
    value=1025.0,
    step=1.0
)

air_density = st.sidebar.number_input(
    "Air density (kg/m³)",
    min_value=0.01,
    value=1.225,
    step=0.01
)


# ------------------------------------------------------------
# Drag
# ------------------------------------------------------------

st.sidebar.subheader("Drag Coefficients")

water_cd = st.sidebar.number_input(
    "Water drag coefficient",
    min_value=0.0,
    value=1.0,
    step=0.1
)

wind_cd = st.sidebar.number_input(
    "Wind drag coefficient",
    min_value=0.0,
    value=1.0,
    step=0.1
)


# ------------------------------------------------------------
# Areas
# ------------------------------------------------------------

st.sidebar.subheader("Areas")

exposed_area = st.sidebar.number_input(
    "Exposed frontal area (m²)",
    min_value=0.01,
    value=100.0,
    step=1.0
)

underwater_area = st.sidebar.number_input(
    "Underwater frontal area (m²)",
    min_value=0.01,
    value=100.0,
    step=1.0
)


# ------------------------------------------------------------
# Wind
# ------------------------------------------------------------

st.sidebar.subheader("🌬️ Wind")

wind_speed = st.sidebar.number_input(
    "Wind speed (m/s)",
    min_value=0.0,
    value=5.0,
    step=0.5
)

wind_direction = st.sidebar.number_input(
    "Wind direction (degrees)",
    value=0.0,
    step=5.0
)


# ------------------------------------------------------------
# Ocean Current
# ------------------------------------------------------------

st.sidebar.subheader("🌊 Ocean Current")

current_speed = st.sidebar.number_input(
    "Current speed (m/s)",
    min_value=0.0,
    value=1.0,
    step=0.1
)

current_direction = st.sidebar.number_input(
    "Current direction (degrees)",
    value=0.0,
    step=5.0
)


# ------------------------------------------------------------
# Latitude
# ------------------------------------------------------------

st.sidebar.subheader("🌍 Latitude")

latitude = st.sidebar.number_input(
    "Latitude (degrees)",
    value=20.0,
    step=1.0
)


# ------------------------------------------------------------
# Initial Position
# ------------------------------------------------------------

st.sidebar.subheader("📍 Initial Position")

x0 = st.sidebar.number_input(
    "Initial X (m)",
    value=0.0,
    step=1.0
)

y0 = st.sidebar.number_input(
    "Initial Y (m)",
    value=0.0,
    step=1.0
)


# ------------------------------------------------------------
# Initial Velocity
# ------------------------------------------------------------

st.sidebar.subheader("🚀 Initial Velocity")

vx0 = st.sidebar.number_input(
    "Initial Vx (m/s)",
    value=0.0,
    step=0.1
)

vy0 = st.sidebar.number_input(
    "Initial Vy (m/s)",
    value=0.0,
    step=0.1
)


# ------------------------------------------------------------
# Simulation
# ------------------------------------------------------------

st.sidebar.subheader("⏱️ Simulation")

total_time = st.sidebar.number_input(
    "Total simulation time (s)",
    min_value=0.01,
    value=100.0,
    step=10.0
)

dt = st.sidebar.number_input(
    "Time step dt (s)",
    min_value=0.0001,
    value=1.0,
    step=0.1
)


# ============================================================
# CREATE ICEBERG
# ============================================================

iceberg = Iceberg(
    length=length,
    width=width,
    height=height,

    ice_density=ice_density,
    water_density=water_density,
    air_density=air_density,

    water_drag_coefficient=water_cd,
    wind_drag_coefficient=wind_cd,

    exposed_area=exposed_area,
    underwater_area=underwater_area,

    wind_speed=wind_speed,
    wind_direction=wind_direction,

    current_speed=current_speed,
    current_direction=current_direction,

    latitude=latitude,

    x0=x0,
    y0=y0,
    vx0=vx0,
    vy0=vy0,

    total_time=total_time,
    dt=dt
)


# ============================================================
# RUN SIMULATION
# ============================================================

if st.sidebar.button(
    "🚀 Run Simulation",
    use_container_width=True
):

    with st.spinner("Calculating iceberg trajectory..."):

        times, states, force_history = simulate(
            iceberg
        )

    # ========================================================
    # FINAL RESULTS
    # ========================================================

    final_state = states[-1]

    final_x = final_state[0]
    final_y = final_state[1]

    final_vx = final_state[2]
    final_vy = final_state[3]

    final_speed = sqrt(
        final_vx**2 + final_vy**2
    )

    final_direction = degrees(
        atan2(final_vy, final_vx)
    )

    if final_direction < 0:
        final_direction += 360

    displacement = sqrt(
        (final_x - iceberg.x0)**2
        + (final_y - iceberg.y0)**2
    )


    # ========================================================
    # PHYSICAL PARAMETERS
    # ========================================================

    st.header("📊 Iceberg Physical Parameters")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Mass",
        f"{iceberg.mass:,.2f} kg"
    )

    col2.metric(
        "Volume",
        f"{iceberg.volume:,.2f} m³"
    )

    col3.metric(
        "Submerged Volume",
        f"{iceberg.submerged_volume:,.2f} m³"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Submerged Fraction",
        f"{iceberg.submerged_fraction:.4f}"
    )

    col2.metric(
        "Weight",
        f"{iceberg.weight:,.2f} N"
    )

    col3.metric(
        "Buoyant Force",
        f"{iceberg.buoyant_force:,.2f} N"
    )


    # ========================================================
    # FINAL POSITION
    # ========================================================

    st.header("📍 Final Position")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Final X",
        f"{final_x:.3f} m"
    )

    col2.metric(
        "Final Y",
        f"{final_y:.3f} m"
    )

    col3.metric(
        "Displacement",
        f"{displacement:.3f} m"
    )


    # ========================================================
    # FINAL VELOCITY
    # ========================================================

    st.header("🚀 Final Velocity")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Vx",
        f"{final_vx:.6f} m/s"
    )

    col2.metric(
        "Vy",
        f"{final_vy:.6f} m/s"
    )

    col3.metric(
        "Speed",
        f"{final_speed:.6f} m/s"
    )

    st.info(
        f"Final direction: **{final_direction:.3f}°**  \n"
        "0° = East, 90° = North, 180° = West, 270° = South"
    )


    # ========================================================
    # TRAJECTORY
    # ========================================================

    st.header("🧭 Iceberg Trajectory")

    x = states[:, 0]
    y = states[:, 1]

    fig1, ax1 = plt.subplots(
        figsize=(10, 6)
    )

    ax1.plot(
        x,
        y,
        linewidth=2,
        label="Iceberg path"
    )

    ax1.scatter(
        iceberg.x0,
        iceberg.y0,
        s=100,
        marker="o",
        label="Initial position"
    )

    ax1.scatter(
        x[-1],
        y[-1],
        s=120,
        marker="X",
        label="Final position"
    )

    ax1.set_title(
        "ICEBERG TRAJECTORY"
    )

    ax1.set_xlabel(
        "X Position (m)"
    )

    ax1.set_ylabel(
        "Y Position (m)"
    )

    ax1.grid(True)
    ax1.legend()

    ax1.set_aspect(
        "equal",
        adjustable="datalim"
    )

    st.pyplot(fig1)


    # ========================================================
    # SPEED VS TIME
    # ========================================================

    st.header("⚡ Speed vs Time")

    vx = states[:, 2]
    vy = states[:, 3]

    speed = np.sqrt(
        vx**2 + vy**2
    )

    fig2, ax2 = plt.subplots(
        figsize=(10, 5)
    )

    ax2.plot(
        times,
        speed,
        linewidth=2
    )

    ax2.set_title(
        "ICEBERG SPEED VS TIME"
    )

    ax2.set_xlabel(
        "Time (s)"
    )

    ax2.set_ylabel(
        "Speed (m/s)"
    )

    ax2.grid(True)

    st.pyplot(fig2)


    # ========================================================
    # VELOCITY COMPONENTS
    # ========================================================

    st.header("📈 Velocity Components")

    fig3, ax3 = plt.subplots(
        figsize=(10, 5)
    )

    ax3.plot(
        times,
        vx,
        label="Vx"
    )

    ax3.plot(
        times,
        vy,
        label="Vy"
    )

    ax3.set_title(
        "VELOCITY COMPONENTS"
    )

    ax3.set_xlabel(
        "Time (s)"
    )

    ax3.set_ylabel(
        "Velocity (m/s)"
    )

    ax3.grid(True)
    ax3.legend()

    st.pyplot(fig3)


    # ========================================================
    # COLORED ICEBERG PATH
    # ========================================================

    st.header("🌈 Iceberg Path Colored by Time")

    fig4, ax4 = plt.subplots(
        figsize=(10, 6)
    )

    scatter = ax4.scatter(
        x,
        y,
        c=times,
        cmap="viridis",
        s=15
    )

    ax4.scatter(
        x[0],
        y[0],
        s=100,
        marker="o",
        label="Start"
    )

    ax4.scatter(
        x[-1],
        y[-1],
        s=120,
        marker="X",
        label="End"
    )

    ax4.set_title(
        "ICEBERG PATH COLORED BY TIME"
    )

    ax4.set_xlabel(
        "X Position (m)"
    )

    ax4.set_ylabel(
        "Y Position (m)"
    )

    ax4.grid(True)
    ax4.legend()

    ax4.set_aspect(
        "equal",
        adjustable="datalim"
    )

    fig4.colorbar(
        scatter,
        ax=ax4,
        label="Time (s)"
    )

    st.pyplot(fig4)


    # ========================================================
    # FORCE INFORMATION
    # ========================================================

    st.header("💨 Forces at Final Time")

    final_forces = force_history[-1]

    force_col1, force_col2 = st.columns(2)

    with force_col1:

        st.write("### Water Drag")

        st.write(
            f"X = {final_forces['water_drag'][0]:.3f} N"
        )

        st.write(
            f"Y = {final_forces['water_drag'][1]:.3f} N"
        )

        st.write("### Wind Force")

        st.write(
            f"X = {final_forces['wind_force'][0]:.3f} N"
        )

        st.write(
            f"Y = {final_forces['wind_force'][1]:.3f} N"
        )

    with force_col2:

        st.write("### Coriolis Force")

        st.write(
            f"X = {final_forces['coriolis_force'][0]:.3f} N"
        )

        st.write(
            f"Y = {final_forces['coriolis_force'][1]:.3f} N"
        )

        st.write("### Total Force")

        st.write(
            f"X = {final_forces['total_force'][0]:.3f} N"
        )

        st.write(
            f"Y = {final_forces['total_force'][1]:.3f} N"
        )


else:

    st.info(
        "👈 Enter the iceberg parameters in the sidebar "
        "and click **Run Simulation**."
    )