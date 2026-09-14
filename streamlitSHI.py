import streamlit as st
import pandas as pd
import numpy as np
import math

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Iceberg Trajectory Simulator",
    page_icon="🧊",
    layout="wide"
)

# ============================================================
# TITLE
# ============================================================

st.title("🧊 Iceberg Trajectory Monitoring System")

st.write(
    """
    This application simulates the 2D motion of an iceberg using
    water-current drag and wind drag forces.
    """
)

st.divider()

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("📍 Initial Position")

x0 = st.sidebar.number_input(
    "Initial X coordinate (m)",
    value=0.0
)

y0 = st.sidebar.number_input(
    "Initial Y coordinate (m)",
    value=0.0
)

# ------------------------------------------------------------

st.sidebar.header("🧊 Iceberg Properties")

mass = st.sidebar.number_input(
    "Mass (kg)",
    min_value=1.0,
    value=100000.0
)

ice_density = st.sidebar.number_input(
    "Ice density (kg/m³)",
    min_value=1.0,
    value=917.0
)

iceberg_length = st.sidebar.number_input(
    "Iceberg length (m)",
    min_value=0.1,
    value=10.0
)

iceberg_width = st.sidebar.number_input(
    "Iceberg width (m)",
    min_value=0.1,
    value=10.0
)

iceberg_height = st.sidebar.number_input(
    "Iceberg height (m)",
    min_value=0.1,
    value=10.0
)

# ------------------------------------------------------------

st.sidebar.header("🌊 Ocean Parameters")

water_density = st.sidebar.number_input(
    "Water density (kg/m³)",
    min_value=1.0,
    value=1025.0
)

current_speed = st.sidebar.number_input(
    "Ocean current speed (m/s)",
    min_value=0.0,
    value=0.5
)

current_direction = st.sidebar.number_input(
    "Ocean current direction (degrees)",
    min_value=0.0,
    max_value=360.0,
    value=0.0
)

water_drag_coefficient = st.sidebar.number_input(
    "Water drag coefficient",
    min_value=0.01,
    value=1.0
)

# ------------------------------------------------------------

st.sidebar.header("💨 Wind Parameters")

wind_speed = st.sidebar.number_input(
    "Wind speed (m/s)",
    min_value=0.0,
    value=5.0
)

wind_direction = st.sidebar.number_input(
    "Wind direction (degrees)",
    min_value=0.0,
    max_value=360.0,
    value=0.0
)

air_density = st.sidebar.number_input(
    "Air density (kg/m³)",
    min_value=0.01,
    value=1.225
)

air_drag_coefficient = st.sidebar.number_input(
    "Wind drag coefficient",
    min_value=0.01,
    value=1.0
)

# ------------------------------------------------------------

st.sidebar.header("🚀 Initial Iceberg Velocity")

initial_speed = st.sidebar.number_input(
    "Initial speed (m/s)",
    min_value=0.0,
    value=0.0
)

initial_direction = st.sidebar.number_input(
    "Initial direction (degrees)",
    min_value=0.0,
    max_value=360.0,
    value=0.0
)

# ------------------------------------------------------------

st.sidebar.header("⏱️ Simulation")

simulation_time = st.sidebar.number_input(
    "Simulation time (seconds)",
    min_value=1.0,
    value=600.0
)

time_step = st.sidebar.number_input(
    "Time step (seconds)",
    min_value=0.01,
    value=1.0
)

# ============================================================
# PHYSICAL CONSTANT
# ============================================================

g = 9.81

# ============================================================
# BASIC ICEBERG CALCULATIONS
# ============================================================

# Volume
volume = mass / ice_density

# Submerged volume using Archimedes principle
submerged_volume = mass / water_density

# Above-water volume
above_water_volume = volume - submerged_volume

# Percentage submerged
submerged_percentage = (
    submerged_volume / volume
) * 100

# Weight
weight = mass * g

# Buoyant force
buoyant_force = water_density * g * submerged_volume

# ============================================================
# AREAS
# ============================================================

# Area exposed to water
water_area = iceberg_width * iceberg_height

# Area exposed to wind
air_area = iceberg_width * iceberg_height

# ============================================================
# CONVERT DIRECTIONS TO VELOCITY VECTORS
# ============================================================

current_angle = math.radians(current_direction)

wind_angle = math.radians(wind_direction)

initial_angle = math.radians(initial_direction)

# Ocean current velocity
current_vx = current_speed * math.cos(current_angle)
current_vy = current_speed * math.sin(current_angle)

# Wind velocity
wind_vx = wind_speed * math.cos(wind_angle)
wind_vy = wind_speed * math.sin(wind_angle)

# Initial iceberg velocity
initial_vx = initial_speed * math.cos(initial_angle)
initial_vy = initial_speed * math.sin(initial_angle)

# ============================================================
# DISPLAY ICEBERG PARAMETERS
# ============================================================

st.subheader("🧊 Iceberg Parameters")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Mass",
    f"{mass:,.2f} kg"
)

c2.metric(
    "Ice Density",
    f"{ice_density:,.2f} kg/m³"
)

c3.metric(
    "Volume",
    f"{volume:,.2f} m³"
)

c4.metric(
    "Submerged Volume",
    f"{submerged_volume:,.2f} m³"
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Submerged %",
    f"{submerged_percentage:.2f}%"
)

c2.metric(
    "Above Water Volume",
    f"{above_water_volume:,.2f} m³"
)

c3.metric(
    "Weight",
    f"{weight:,.2f} N"
)

c4.metric(
    "Buoyant Force",
    f"{buoyant_force:,.2f} N"
)

# ============================================================
# SIMULATION BUTTON
# ============================================================

st.divider()

run_simulation = st.button(
    "🚀 Run Iceberg Simulation",
    type="primary"
)

# ============================================================
# SIMULATION
# ============================================================

if run_simulation:

    # Number of simulation steps
    num_steps = int(simulation_time / time_step) + 1

    # --------------------------------------------------------
    # ARRAYS
    # --------------------------------------------------------

    time = np.zeros(num_steps)

    x = np.zeros(num_steps)
    y = np.zeros(num_steps)

    vx = np.zeros(num_steps)
    vy = np.zeros(num_steps)

    ax = np.zeros(num_steps)
    ay = np.zeros(num_steps)

    speed = np.zeros(num_steps)

    water_fx = np.zeros(num_steps)
    water_fy = np.zeros(num_steps)

    wind_fx = np.zeros(num_steps)
    wind_fy = np.zeros(num_steps)

    net_fx = np.zeros(num_steps)
    net_fy = np.zeros(num_steps)

    # --------------------------------------------------------
    # INITIAL CONDITIONS
    # --------------------------------------------------------

    x[0] = x0
    y[0] = y0

    vx[0] = initial_vx
    vy[0] = initial_vy

    speed[0] = math.sqrt(
        vx[0] ** 2 +
        vy[0] ** 2
    )

    # --------------------------------------------------------
    # TIME LOOP
    # --------------------------------------------------------

    for i in range(num_steps - 1):

        # ====================================================
        # WATER RELATIVE VELOCITY
        # ====================================================

        relative_water_x = current_vx - vx[i]

        relative_water_y = current_vy - vy[i]

        relative_water_speed = math.sqrt(
            relative_water_x ** 2 +
            relative_water_y ** 2
        )

        # ====================================================
        # WATER DRAG
        # ====================================================

        water_fx[i] = (
            0.5
            * water_drag_coefficient
            * water_density
            * water_area
            * relative_water_speed
            * relative_water_x
        )

        water_fy[i] = (
            0.5
            * water_drag_coefficient
            * water_density
            * water_area
            * relative_water_speed
            * relative_water_y
        )

        # ====================================================
        # WIND RELATIVE VELOCITY
        # ====================================================

        relative_wind_x = wind_vx - vx[i]

        relative_wind_y = wind_vy - vy[i]

        relative_wind_speed = math.sqrt(
            relative_wind_x ** 2 +
            relative_wind_y ** 2
        )

        # ====================================================
        # WIND DRAG
        # ====================================================

        wind_fx[i] = (
            0.5
            * air_drag_coefficient
            * air_density
            * air_area
            * relative_wind_speed
            * relative_wind_x
        )

        wind_fy[i] = (
            0.5
            * air_drag_coefficient
            * air_density
            * air_area
            * relative_wind_speed
            * relative_wind_y
        )

        # ====================================================
        # NET FORCE
        # ====================================================

        net_fx[i] = (
            water_fx[i] +
            wind_fx[i]
        )

        net_fy[i] = (
            water_fy[i] +
            wind_fy[i]
        )

        # ====================================================
        # ACCELERATION
        # ====================================================

        ax[i] = net_fx[i] / mass

        ay[i] = net_fy[i] / mass

        # ====================================================
        # VELOCITY UPDATE
        # ====================================================

        vx[i + 1] = (
            vx[i] +
            ax[i] * time_step
        )

        vy[i + 1] = (
            vy[i] +
            ay[i] * time_step
        )

        # ====================================================
        # POSITION UPDATE
        # ====================================================

        x[i + 1] = (
            x[i] +
            vx[i + 1] * time_step
        )

        y[i + 1] = (
            y[i] +
            vy[i + 1] * time_step
        )

        # ====================================================
        # TIME
        # ====================================================

        time[i + 1] = (
            time[i] +
            time_step
        )

        # ====================================================
        # SPEED
        # ====================================================

        speed[i + 1] = math.sqrt(
            vx[i + 1] ** 2 +
            vy[i + 1] ** 2
        )

    # ========================================================
    # FINAL VALUES
    # ========================================================

    final_x = x[-1]
    final_y = y[-1]

    final_vx = vx[-1]
    final_vy = vy[-1]

    final_speed = math.sqrt(
        final_vx ** 2 +
        final_vy ** 2
    )

    displacement_x = final_x - x0

    displacement_y = final_y - y0

    displacement = math.sqrt(
        displacement_x ** 2 +
        displacement_y ** 2
    )

    # ========================================================
    # DIRECTION
    # ========================================================

    direction = math.degrees(
        math.atan2(
            displacement_y,
            displacement_x
        )
    )

    if direction < 0:
        direction += 360

    # --------------------------------------------------------
    # FINAL VELOCITY DIRECTION
    # --------------------------------------------------------

    velocity_direction = math.degrees(
        math.atan2(
            final_vy,
            final_vx
        )
    )

    if velocity_direction < 0:
        velocity_direction += 360

    # ========================================================
    # DIRECTION NAME
    # ========================================================

    def get_direction(angle):

        directions = [
            "East",
            "North-East",
            "North",
            "North-West",
            "West",
            "South-West",
            "South",
            "South-East"
        ]

        index = int(
            ((angle + 22.5) % 360) / 45
        )

        return directions[index]

    direction_name = get_direction(direction)

    # ========================================================
    # RESULTS
    # ========================================================

    st.divider()

    st.subheader("🎯 Final Results")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Final X",
        f"{final_x:,.2f} m"
    )

    c2.metric(
        "Final Y",
        f"{final_y:,.2f} m"
    )

    c3.metric(
        "Displacement",
        f"{displacement:,.2f} m"
    )

    c4.metric(
        "Final Speed",
        f"{final_speed:.4f} m/s"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Travel Direction",
        f"{direction:.2f}°"
    )

    c2.metric(
        "Direction",
        direction_name
    )

    c3.metric(
        "Final Velocity Direction",
        f"{velocity_direction:.2f}°"
    )

    # ========================================================
    # RESULT MESSAGE
    # ========================================================

    st.success(
        f"""
        🧭 **Iceberg trajectory completed**

        Initial position: ({x0:.2f}, {y0:.2f}) m

        Final position: ({final_x:.2f}, {final_y:.2f}) m

        Total displacement: {displacement:.2f} m

        Direction: {direction:.2f}° ({direction_name})

        Final velocity: ({final_vx:.4f}, {final_vy:.4f}) m/s
        """
    )

    # ========================================================
    # TRAJECTORY
    # ========================================================

    st.divider()

    st.subheader("🗺️ Iceberg Trajectory Visualization")

    trajectory_df = pd.DataFrame(
        {
            "X Position (m)": x,
            "Y Position (m)": y
        }
    )

    # Streamlit native line chart
    st.line_chart(
        trajectory_df,
        x="X Position (m)",
        y="Y Position (m)",
        height=500
    )

    st.caption(
        "The line represents the calculated path of the iceberg. "
        "The X-axis represents east/west displacement and the Y-axis "
        "represents north/south displacement."
    )

    # ========================================================
    # VELOCITY GRAPH
    # ========================================================

    st.subheader("🚀 Iceberg Speed vs Time")

    speed_df = pd.DataFrame(
        {
            "Time (s)": time,
            "Speed (m/s)": speed
        }
    )

    st.line_chart(
        speed_df,
        x="Time (s)",
        y="Speed (m/s)",
        height=400
    )

    # ========================================================
    # X AND Y POSITION
    # ========================================================

    st.subheader("📍 Position vs Time")

    position_df = pd.DataFrame(
        {
            "Time (s)": time,
            "X Position (m)": x,
            "Y Position (m)": y
        }
    )

    st.line_chart(
        position_df,
        x="Time (s)",
        y=[
            "X Position (m)",
            "Y Position (m)"
        ],
        height=400
    )

    # ========================================================
    # FORCES
    # ========================================================

    st.subheader("⚙️ Forces")

    water_force = np.sqrt(
        water_fx ** 2 +
        water_fy ** 2
    )

    wind_force = np.sqrt(
        wind_fx ** 2 +
        wind_fy ** 2
    )

    net_force = np.sqrt(
        net_fx ** 2 +
        net_fy ** 2
    )

    force_df = pd.DataFrame(
        {
            "Time (s)": time,
            "Water Drag (N)": water_force,
            "Wind Drag (N)": wind_force,
            "Net Force (N)": net_force
        }
    )

    st.line_chart(
        force_df,
        x="Time (s)",
        y=[
            "Water Drag (N)",
            "Wind Drag (N)",
            "Net Force (N)"
        ],
        height=400
    )

    # ========================================================
    # SIMULATION TABLE
    # ========================================================

    st.subheader("📊 Simulation Data")

    simulation_df = pd.DataFrame(
        {
            "Time (s)": time,
            "X (m)": x,
            "Y (m)": y,
            "Vx (m/s)": vx,
            "Vy (m/s)": vy,
            "Speed (m/s)": speed,
            "Ax (m/s²)": ax,
            "Ay (m/s²)": ay,
            "Water Fx (N)": water_fx,
            "Water Fy (N)": water_fy,
            "Wind Fx (N)": wind_fx,
            "Wind Fy (N)": wind_fy,
            "Net Fx (N)": net_fx,
            "Net Fy (N)": net_fy
        }
    )

    st.dataframe(
        simulation_df,
        use_container_width=True
    )

    # ========================================================
    # DOWNLOAD CSV
    # ========================================================

    csv = simulation_df.to_csv(
        index=False
    )

    st.download_button(
        label="⬇️ Download Simulation CSV",
        data=csv,
        file_name="iceberg_trajectory.csv",
        mime="text/csv"
    )

# ============================================================
# FORMULAS
# ============================================================

st.divider()

st.subheader("📐 Mathematical Model")

st.markdown(
    """
### 1. Iceberg volume

\[
V = \\frac{m}{\\rho_{ice}}
\]

### 2. Submerged volume

For a floating iceberg:

\[
V_{sub} = \\frac{m}{\\rho_{water}}
\]

### 3. Weight

\[
F_g = mg
\]

### 4. Buoyant force

\[
F_B = \\rho_{water}gV_{sub}
\]

For a freely floating iceberg:

\[
F_B \\approx F_g
\]

### 5. Water drag force

\[
F_{water}
=
\\frac{1}{2}
C_d
\\rho_w
A
|V_w-V_i|
(V_w-V_i)
\]

### 6. Wind drag force

\[
F_{wind}
=
\\frac{1}{2}
C_d
\\rho_a
A
|V_{wind}-V_i|
(V_{wind}-V_i)
\]

### 7. Net horizontal force

\[
F_{net}=F_{water}+F_{wind}
\]

### 8. Acceleration

\[
a=\\frac{F_{net}}{m}
\]

### 9. Velocity

\[
V_{new}=V_{old}+a\\Delta t
\]

### 10. Position

\[
X_{new}=X_{old}+V_x\\Delta t
\]

\[
Y_{new}=Y_{old}+V_y\\Delta t
\]

### 11. Displacement

\[
D=
\\sqrt{
(X_f-X_0)^2+
(Y_f-Y_0)^2
}
\]

### 12. Direction

\[
\\theta=
atan2(Y_f-Y_0,X_f-X_0)
\]

The direction is converted to degrees and expressed as
East, North-East, North, North-West, West, South-West,
South or South-East.
"""
)

st.info(
    """
    This is a simplified 2D iceberg dynamics model. Real iceberg
    trajectories can additionally involve ocean currents varying with
    depth, waves, Coriolis force, rotational motion, iceberg geometry,
    waterline changes and wave-induced forces.
    """
)
