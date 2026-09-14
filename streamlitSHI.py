import streamlit as st
import numpy as np
import pandas as pd

import math

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Iceberg Trajectory Simulator",
    page_icon="🧊",
    layout="wide"
)

st.title("🧊 Iceberg Trajectory Monitoring & Simulation System")

st.write(
    """
    This application calculates the motion of an iceberg using a simplified
    2D force-balance model. Enter the physical and environmental parameters
    below to calculate the iceberg's trajectory, final coordinates, velocity,
    forces and direction.
    """
)

# ---------------------------------------------------------
# SIDEBAR INPUTS
# ---------------------------------------------------------

st.sidebar.header("📍 Initial Position")

x0 = st.sidebar.number_input(
    "Initial X coordinate (m)",
    value=0.0
)

y0 = st.sidebar.number_input(
    "Initial Y coordinate (m)",
    value=0.0
)

st.sidebar.header("🧊 Iceberg Properties")

mass = st.sidebar.number_input(
    "Iceberg mass (kg)",
    min_value=1.0,
    value=100000.0
)

ice_density = st.sidebar.number_input(
    "Ice density (kg/m³)",
    min_value=1.0,
    value=917.0
)

iceberg_height = st.sidebar.number_input(
    "Iceberg height (m)",
    min_value=0.1,
    value=10.0
)

iceberg_width = st.sidebar.number_input(
    "Iceberg width (m)",
    min_value=0.1,
    value=10.0
)

iceberg_length = st.sidebar.number_input(
    "Iceberg length (m)",
    min_value=0.1,
    value=10.0
)

st.sidebar.header("🌊 Water Properties")

water_density = st.sidebar.number_input(
    "Water density (kg/m³)",
    min_value=1.0,
    value=1025.0
)

water_current_speed = st.sidebar.number_input(
    "Water current speed (m/s)",
    min_value=0.0,
    value=0.5
)

water_current_direction = st.sidebar.number_input(
    "Water current direction (degrees)",
    min_value=0.0,
    max_value=360.0,
    value=0.0,
    help="0° = +X direction, 90° = +Y direction"
)

water_drag_coefficient = st.sidebar.number_input(
    "Water drag coefficient",
    min_value=0.01,
    value=1.0
)

st.sidebar.header("💨 Wind Properties")

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
    "Air drag coefficient",
    min_value=0.01,
    value=1.0
)

st.sidebar.header("🚀 Initial Velocity")

initial_speed = st.sidebar.number_input(
    "Initial iceberg speed (m/s)",
    min_value=0.0,
    value=0.0
)

initial_direction = st.sidebar.number_input(
    "Initial iceberg direction (degrees)",
    min_value=0.0,
    max_value=360.0,
    value=0.0
)

st.sidebar.header("⏱️ Simulation")

simulation_time = st.sidebar.number_input(
    "Simulation time (seconds)",
    min_value=1.0,
    value=600.0
)

time_step = st.sidebar.number_input(
    "Time step Δt (seconds)",
    min_value=0.01,
    value=1.0
)

# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

g = 9.81

# ---------------------------------------------------------
# CALCULATIONS
# ---------------------------------------------------------

# Iceberg volume
volume = mass / ice_density

# Approximate submerged volume from Archimedes principle
submerged_volume = mass / water_density

# Percentage submerged
submerged_percentage = (
    submerged_volume / volume
) * 100

# Above-water volume
above_water_volume = volume - submerged_volume

# Iceberg cross-sectional areas
water_area = iceberg_width * iceberg_height
air_area = iceberg_width * iceberg_height

# Weight
weight = mass * g

# Buoyant force
buoyant_force = water_density * g * submerged_volume

# Convert angles to radians
water_angle_rad = math.radians(water_current_direction)
wind_angle_rad = math.radians(wind_direction)
initial_angle_rad = math.radians(initial_direction)

# Water velocity vector
water_vx = water_current_speed * math.cos(water_angle_rad)
water_vy = water_current_speed * math.sin(water_angle_rad)

# Wind velocity vector
wind_vx = wind_speed * math.cos(wind_angle_rad)
wind_vy = wind_speed * math.sin(wind_angle_rad)

# Initial iceberg velocity
vx_initial = initial_speed * math.cos(initial_angle_rad)
vy_initial = initial_speed * math.sin(initial_angle_rad)

# ---------------------------------------------------------
# DISPLAY BASIC ICEBERG PARAMETERS
# ---------------------------------------------------------

st.subheader("🧊 Iceberg Parameters")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Mass",
    f"{mass:,.2f} kg"
)

col2.metric(
    "Ice Density",
    f"{ice_density:,.2f} kg/m³"
)

col3.metric(
    "Total Volume",
    f"{volume:,.2f} m³"
)

col4.metric(
    "Submerged Volume",
    f"{submerged_volume:,.2f} m³"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Above-water Volume",
    f"{above_water_volume:,.2f} m³"
)

col2.metric(
    "Submerged %",
    f"{submerged_percentage:.2f}%"
)

col3.metric(
    "Weight",
    f"{weight:,.2f} N"
)

col4.metric(
    "Buoyant Force",
    f"{buoyant_force:,.2f} N"
)

# ---------------------------------------------------------
# FORCE EXPLANATION
# ---------------------------------------------------------

st.subheader("⚙️ Physics Model")

st.markdown(
    f"""
### 1. Iceberg volume

$$
V = \\frac{{m}}{{\\rho_{{ice}}}}
$$

$$
V = \\frac{{{mass:,.2f}}}{{{ice_density:,.2f}}}
= {volume:,.2f}\\ m^3
$$

### 2. Submerged volume

For a floating iceberg:

$$
F_B = mg
$$

and

$$
F_B = \\rho_w g V_{{submerged}}
$$

Therefore:

$$
V_{{submerged}} =
\\frac{{m}}{{\\rho_w}}
$$

### 3. Weight

$$
F_g = mg
$$

### 4. Water drag

$$
F_{{water}} =
\\frac12 C_d \\rho_w A
|\\vec{{v}}_w-\\vec{{v}}|
(\\vec{{v}}_w-\\vec{{v}})
$$

### 5. Wind drag

$$
F_{{wind}} =
\\frac12 C_d \\rho_a A
|\\vec{{v}}_{{wind}}-\\vec{{v}}|
(\\vec{{v}}_{{wind}}-\\vec{{v}})
$$

### 6. Net horizontal force

$$
\\vec{{F}}_{{net}}
=
\\vec{{F}}_{{water}}
+
\\vec{{F}}_{{wind}}
$$

### 7. Acceleration

$$
\\vec{{a}} =
\\frac{{\\vec{{F}}_{{net}}}}{{m}}
$$
"""
)

# ---------------------------------------------------------
# SIMULATION
# ---------------------------------------------------------

num_steps = int(simulation_time / time_step) + 1

times = np.zeros(num_steps)

x = np.zeros(num_steps)
y = np.zeros(num_steps)

vx = np.zeros(num_steps)
vy = np.zeros(num_steps)

ax = np.zeros(num_steps)
ay = np.zeros(num_steps)

water_fx = np.zeros(num_steps)
water_fy = np.zeros(num_steps)

wind_fx = np.zeros(num_steps)
wind_fy = np.zeros(num_steps)

net_fx = np.zeros(num_steps)
net_fy = np.zeros(num_steps)

speed = np.zeros(num_steps)

# Initial conditions
x[0] = x0
y[0] = y0

vx[0] = vx_initial
vy[0] = vy_initial

# ---------------------------------------------------------
# TIME INTEGRATION
# ---------------------------------------------------------

for i in range(num_steps - 1):

    # -----------------------------------------------------
    # RELATIVE WATER VELOCITY
    # -----------------------------------------------------

    relative_water_vx = water_vx - vx[i]
    relative_water_vy = water_vy - vy[i]

    relative_water_speed = math.sqrt(
        relative_water_vx**2 +
        relative_water_vy**2
    )

    # -----------------------------------------------------
    # WATER DRAG FORCE
    # -----------------------------------------------------

    if relative_water_speed > 0:

        water_fx[i] = (
            0.5
            * water_drag_coefficient
            * water_density
            * water_area
            * relative_water_speed
            * relative_water_vx
        )

        water_fy[i] = (
            0.5
            * water_drag_coefficient
            * water_density
            * water_area
            * relative_water_speed
            * relative_water_vy
        )

    # -----------------------------------------------------
    # RELATIVE WIND VELOCITY
    # -----------------------------------------------------

    relative_wind_vx = wind_vx - vx[i]
    relative_wind_vy = wind_vy - vy[i]

    relative_wind_speed = math.sqrt(
        relative_wind_vx**2 +
        relative_wind_vy**2
    )

    # -----------------------------------------------------
    # WIND DRAG FORCE
    # -----------------------------------------------------

    if relative_wind_speed > 0:

        wind_fx[i] = (
            0.5
            * air_drag_coefficient
            * air_density
            * air_area
            * relative_wind_speed
            * relative_wind_vx
        )

        wind_fy[i] = (
            0.5
            * air_drag_coefficient
            * air_density
            * air_area
            * relative_wind_speed
            * relative_wind_vy
        )

    # -----------------------------------------------------
    # NET FORCE
    # -----------------------------------------------------

    net_fx[i] = water_fx[i] + wind_fx[i]
    net_fy[i] = water_fy[i] + wind_fy[i]

    # -----------------------------------------------------
    # ACCELERATION
    # -----------------------------------------------------

    ax[i] = net_fx[i] / mass
    ay[i] = net_fy[i] / mass

    # -----------------------------------------------------
    # UPDATE VELOCITY
    # -----------------------------------------------------

    vx[i + 1] = vx[i] + ax[i] * time_step
    vy[i + 1] = vy[i] + ay[i] * time_step

    # -----------------------------------------------------
    # UPDATE POSITION
    # -----------------------------------------------------

    x[i + 1] = x[i] + vx[i + 1] * time_step
    y[i + 1] = y[i] + vy[i + 1] * time_step

    times[i + 1] = times[i] + time_step

    # -----------------------------------------------------
    # SPEED
    # -----------------------------------------------------

    speed[i + 1] = math.sqrt(
        vx[i + 1]**2 +
        vy[i + 1]**2
    )

# Calculate final forces
water_fx[-1] = water_fx[-2]
water_fy[-1] = water_fy[-2]

wind_fx[-1] = wind_fx[-2]
wind_fy[-1] = wind_fy[-2]

net_fx[-1] = water_fx[-1] + wind_fx[-1]
net_fy[-1] = water_fy[-1] + wind_fy[-1]

ax[-1] = net_fx[-1] / mass
ay[-1] = net_fy[-1] / mass

speed[0] = math.sqrt(
    vx[0]**2 + vy[0]**2
)

# ---------------------------------------------------------
# FINAL RESULTS
# ---------------------------------------------------------

final_x = x[-1]
final_y = y[-1]

final_vx = vx[-1]
final_vy = vy[-1]

final_speed = math.sqrt(
    final_vx**2 + final_vy**2
)

displacement_x = final_x - x0
displacement_y = final_y - y0

total_displacement = math.sqrt(
    displacement_x**2 +
    displacement_y**2
)

# Direction of final displacement
direction = math.degrees(
    math.atan2(displacement_y, displacement_x)
)

if direction < 0:
    direction += 360

# Final velocity direction
velocity_direction = math.degrees(
    math.atan2(final_vy, final_vx)
)

if velocity_direction < 0:
    velocity_direction += 360

# ---------------------------------------------------------
# RESULT DISPLAY
# ---------------------------------------------------------

st.subheader("🎯 Final Trajectory Results")

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
    f"{total_displacement:,.2f} m"
)

c4.metric(
    "Final Speed",
    f"{final_speed:,.3f} m/s"
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "Travel Direction",
    f"{direction:.2f}°"
)

c2.metric(
    "Final Velocity Direction",
    f"{velocity_direction:.2f}°"
)

c3.metric(
    "Simulation Time",
    f"{simulation_time:,.1f} s"
)

# ---------------------------------------------------------
# DIRECTION DESCRIPTION
# ---------------------------------------------------------

def direction_name(angle):

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


st.success(
    f"""
    🧭 The iceberg travels approximately **{direction:.2f}°**
    ({direction_name(direction)}).

    Final position:
    **({final_x:.2f} m, {final_y:.2f} m)**

    Total displacement:
    **{total_displacement:.2f} m**
    """
)

# ---------------------------------------------------------
# TRAJECTORY VISUALIZATION
# ---------------------------------------------------------

st.subheader("🗺️ Iceberg Trajectory")

fig, ax_plot = plt.subplots(figsize=(12, 7))

ax_plot.plot(
    x,
    y,
    linewidth=2,
    label="Iceberg trajectory"
)

# Initial position
ax_plot.scatter(
    x[0],
    y[0],
    s=100,
    marker="o",
    label="Initial position"
)

# Final position
ax_plot.scatter(
    x[-1],
    y[-1],
    s=150,
    marker="X",
    label="Final position"
)

# Direction arrow
arrow_index = max(
    1,
    int(len(x) * 0.75)
)

dx_arrow = x[arrow_index] - x[arrow_index - 1]
dy_arrow = y[arrow_index] - y[arrow_index - 1]

ax_plot.arrow(
    x[arrow_index - 1],
    y[arrow_index - 1],
    dx_arrow,
    dy_arrow,
    head_width=max(total_displacement * 0.02, 1),
    head_length=max(total_displacement * 0.03, 1),
    length_includes_head=True
)

ax_plot.set_xlabel("X Position (m)")
ax_plot.set_ylabel("Y Position (m)")
ax_plot.set_title("Simulated Iceberg Trajectory")

ax_plot.grid(True)
ax_plot.legend()

ax_plot.set_aspect("equal", adjustable="datalim")

st.pyplot(fig)

# ---------------------------------------------------------
# VELOCITY GRAPH
# ---------------------------------------------------------

st.subheader("🚀 Iceberg Speed vs Time")

fig2, ax2 = plt.subplots(figsize=(12, 5))

ax2.plot(
    times,
    speed,
    linewidth=2
)

ax2.set_xlabel("Time (s)")
ax2.set_ylabel("Speed (m/s)")
ax2.set_title("Iceberg Speed vs Time")

ax2.grid(True)

st.pyplot(fig2)

# ---------------------------------------------------------
# FORCE GRAPH
# ---------------------------------------------------------

st.subheader("⚙️ Forces vs Time")

fig3, ax3 = plt.subplots(figsize=(12, 5))

water_force_magnitude = np.sqrt(
    water_fx**2 +
    water_fy**2
)

wind_force_magnitude = np.sqrt(
    wind_fx**2 +
    wind_fy**2
)

net_force_magnitude = np.sqrt(
    net_fx**2 +
    net_fy**2
)

ax3.plot(
    times,
    water_force_magnitude,
    label="Water drag"
)

ax3.plot(
    times,
    wind_force_magnitude,
    label="Wind drag"
)

ax3.plot(
    times,
    net_force_magnitude,
    label="Net force"
)

ax3.set_xlabel("Time (s)")
ax3.set_ylabel("Force (N)")
ax3.set_title("Iceberg Forces vs Time")

ax3.grid(True)
ax3.legend()

st.pyplot(fig3)

# ---------------------------------------------------------
# DATA TABLE
# ---------------------------------------------------------

st.subheader("📊 Simulation Data")

data = pd.DataFrame({
    "Time (s)": times,
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
})

st.dataframe(
    data,
    use_container_width=True
)

# ---------------------------------------------------------
# DOWNLOAD CSV
# ---------------------------------------------------------

csv = data.to_csv(index=False)

st.download_button(
    label="⬇️ Download Simulation Data (CSV)",
    data=csv,
    file_name="iceberg_trajectory.csv",
    mime="text/csv"
)

# ---------------------------------------------------------
# FORMULA SUMMARY
# ---------------------------------------------------------

st.subheader("📐 Formula Summary")

st.markdown(
    """
### Iceberg volume

`V = m / ρ_ice`

### Submerged volume

`V_sub = m / ρ_water`

### Weight

`Fg = m × g`

### Buoyant force

`Fb = ρ_water × g × V_sub`

### Water drag

`F_water = ½ × Cd × ρ_water × A × |Vwater - Vice| × (Vwater - Vice)`

### Wind drag

`F_wind = ½ × Cd × ρ_air × A × |Vwind - Vice| × (Vwind - Vice)`

### Net force

`F_net = F_water + F_wind`

### Acceleration

`a = F_net / m`

### Velocity

`V_new = V_old + a × Δt`

### Position

`X_new = X_old + Vx_new × Δt`

`Y_new = Y_old + Vy_new × Δt`

### Displacement

`D = √((X_final-X_initial)² + (Y_final-Y_initial)²)`

### Direction

`θ = atan2(Y_final-Y_initial, X_final-X_initial)`
"""
)

st.caption(
    "Note: This is a simplified 2D engineering simulation. "
    "Real iceberg motion can also depend on waves, ocean currents varying "
    "with depth, Coriolis force, rotational dynamics, iceberg shape, "
    "keel geometry, wave radiation, and sea-ice interactions."
)
