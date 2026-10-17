"""Grid rectifier scheduling and SoC PI control, separate from PCS dynamics."""


def grid_power_reference(filtered_load_w, soc_pct, integral_pct_s, startup, config):
    """Return unsaturated grid reference (W) and integral derivative (%).

    Startup commands rated rectifier power. After handover, load feedforward
    plus SoC PI regulates energy. Conditional integration prevents windup.
    Load feedforward is low-pass filtered by a state in simulation.py.
    The battery supplies the remaining fast load component.
    """
    error_pct = config.target_soc_pct - soc_pct
    if startup:
        return config.rated_power_w, 0.0
    reference_w = (filtered_load_w + config.kp_w_per_pct*error_pct
                   + config.ki_w_per_pct_s*integral_pct_s)
    saturated_outward = ((reference_w >= config.rated_power_w and error_pct > 0)
                         or (reference_w <= 0 and error_pct < 0))
    return reference_w, 0.0 if saturated_outward else error_pct
