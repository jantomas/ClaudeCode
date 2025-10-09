/**
 * Inverse Kinematics Solver for Hexapod Legs
 *
 * Uses analytical IK solution for 3-DOF leg (coxa, femur, tibia)
 * Compiled as shared library for Python integration
 */

#include <cmath>
#include <algorithm>
#include <stdexcept>

// Struct for 3D position
struct Position3D {
    double x;
    double y;
    double z;
};

// Struct for joint angles (in radians)
struct JointAngles {
    double coxa;   // Hip rotation
    double femur;  // Upper leg angle
    double tibia;  // Lower leg angle
};

// Struct for leg dimensions
struct LegDimensions {
    double coxa_length;   // Length of coxa (hip segment)
    double femur_length;  // Length of femur (upper leg)
    double tibia_length;  // Length of tibia (lower leg)
};

/**
 * Convert degrees to radians
 */
inline double deg_to_rad(double degrees) {
    return degrees * M_PI / 180.0;
}

/**
 * Convert radians to degrees
 */
inline double rad_to_deg(double radians) {
    return radians * 180.0 / M_PI;
}

/**
 * Clamp angle to valid servo range
 */
inline double clamp_angle(double angle_deg, double min_deg = 0.0, double max_deg = 180.0) {
    return std::max(min_deg, std::min(max_deg, angle_deg));
}

/**
 * Solve inverse kinematics for a single leg
 *
 * @param target Target foot position in leg coordinate system
 * @param dimensions Leg segment lengths
 * @return Joint angles (in degrees)
 * @throws std::runtime_error if target is unreachable
 */
extern "C" JointAngles solve_ik(const Position3D& target, const LegDimensions& dimensions) {
    JointAngles angles;

    // Step 1: Calculate coxa angle (rotation in XY plane)
    // Coxa rotates the leg horizontally
    double coxa_angle_rad = atan2(target.y, target.x);

    // Distance from coxa joint to target in XY plane
    double xy_distance = sqrt(target.x * target.x + target.y * target.y);

    // Account for coxa length - femur starts after coxa
    double femur_base_distance = xy_distance - dimensions.coxa_length;

    // Step 2: Calculate femur and tibia angles (in XZ plane)
    // This is a 2D IK problem in the sagittal plane

    // Distance from femur base to target foot
    double horizontal_reach = femur_base_distance;
    double vertical_reach = target.z;
    double reach_distance = sqrt(horizontal_reach * horizontal_reach +
                                  vertical_reach * vertical_reach);

    // Check if target is reachable
    double max_reach = dimensions.femur_length + dimensions.tibia_length;
    double min_reach = fabs(dimensions.femur_length - dimensions.tibia_length);

    if (reach_distance > max_reach) {
        throw std::runtime_error("Target position is too far (unreachable)");
    }

    if (reach_distance < min_reach) {
        throw std::runtime_error("Target position is too close (unreachable)");
    }

    // Use law of cosines to find tibia angle
    // cos(tibia_angle) = (femur² + tibia² - reach²) / (2 * femur * tibia)
    double cos_tibia = (dimensions.femur_length * dimensions.femur_length +
                        dimensions.tibia_length * dimensions.tibia_length -
                        reach_distance * reach_distance) /
                       (2.0 * dimensions.femur_length * dimensions.tibia_length);

    // Clamp to valid range for acos
    cos_tibia = std::max(-1.0, std::min(1.0, cos_tibia));

    double tibia_angle_rad = acos(cos_tibia);

    // Calculate femur angle
    // First, find angle from horizontal to reach vector
    double reach_angle = atan2(vertical_reach, horizontal_reach);

    // Then, use law of cosines to find angle between femur and reach line
    double cos_femur_offset = (dimensions.femur_length * dimensions.femur_length +
                               reach_distance * reach_distance -
                               dimensions.tibia_length * dimensions.tibia_length) /
                              (2.0 * dimensions.femur_length * reach_distance);

    cos_femur_offset = std::max(-1.0, std::min(1.0, cos_femur_offset));
    double femur_offset_angle = acos(cos_femur_offset);

    double femur_angle_rad = reach_angle + femur_offset_angle;

    // Convert to degrees and adjust for servo conventions
    angles.coxa = rad_to_deg(coxa_angle_rad);
    angles.femur = rad_to_deg(femur_angle_rad);

    // Tibia angle is relative to femur (180 degrees - interior angle)
    angles.tibia = 180.0 - rad_to_deg(tibia_angle_rad);

    // Clamp angles to valid servo range [0, 180]
    angles.coxa = clamp_angle(angles.coxa + 90.0);  // Offset for 0-180 range
    angles.femur = clamp_angle(angles.femur + 90.0);
    angles.tibia = clamp_angle(angles.tibia);

    return angles;
}

/**
 * Forward kinematics - calculate foot position from joint angles
 * Useful for validation and testing
 *
 * @param angles Joint angles (in degrees)
 * @param dimensions Leg segment lengths
 * @return Foot position in leg coordinate system
 */
extern "C" Position3D solve_fk(const JointAngles& angles, const LegDimensions& dimensions) {
    Position3D position;

    // Convert angles from servo range [0, 180] back to working range
    double coxa_rad = deg_to_rad(angles.coxa - 90.0);
    double femur_rad = deg_to_rad(angles.femur - 90.0);
    double tibia_interior_rad = deg_to_rad(180.0 - angles.tibia);

    // Coxa contribution (horizontal rotation)
    double coxa_x = dimensions.coxa_length * cos(coxa_rad);
    double coxa_y = dimensions.coxa_length * sin(coxa_rad);

    // Femur contribution
    double femur_horizontal = dimensions.femur_length * cos(femur_rad);
    double femur_vertical = dimensions.femur_length * sin(femur_rad);

    // Tibia angle relative to ground (femur angle + tibia angle)
    double tibia_abs_angle = femur_rad + tibia_interior_rad - M_PI;
    double tibia_horizontal = dimensions.tibia_length * cos(tibia_abs_angle);
    double tibia_vertical = dimensions.tibia_length * sin(tibia_abs_angle);

    // Total position
    double total_horizontal = femur_horizontal + tibia_horizontal;

    position.x = coxa_x + total_horizontal * cos(coxa_rad);
    position.y = coxa_y + total_horizontal * sin(coxa_rad);
    position.z = femur_vertical + tibia_vertical;

    return position;
}

/**
 * Validate if a position is reachable
 *
 * @param target Target position
 * @param dimensions Leg dimensions
 * @return true if reachable, false otherwise
 */
extern "C" bool is_reachable(const Position3D& target, const LegDimensions& dimensions) {
    try {
        solve_ik(target, dimensions);
        return true;
    } catch (const std::runtime_error&) {
        return false;
    }
}

/**
 * Calculate workspace boundary (maximum reach at given height)
 *
 * @param z_height Height (z coordinate)
 * @param dimensions Leg dimensions
 * @return Maximum horizontal reach at this height
 */
extern "C" double max_reach_at_height(double z_height, const LegDimensions& dimensions) {
    double max_leg_length = dimensions.femur_length + dimensions.tibia_length;

    // Using Pythagorean theorem
    double horizontal_reach = sqrt(max_leg_length * max_leg_length - z_height * z_height);

    // Add coxa length
    return horizontal_reach + dimensions.coxa_length;
}
