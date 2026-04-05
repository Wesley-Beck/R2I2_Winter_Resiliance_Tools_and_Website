"""
NFDRS Fire Danger Indices: ERC, SC, BI.

Ported directly from Argonne's ERC/BI code (Yu/Feng), with cross-validation
against firelab/NFDRS4-TechDoc NFDRSV4Calc.py.

Key implementation details matching Argonne:
- SC moisture damping: Anderson (1969) coefficients: η = 1 - 2.59r + 5.11r² - 3.52r³
- ERC moisture damping: Albini (1976) coefficients: η = 1 - 2r + 1.5r² - 0.5r³
- BI = 3.01 × (SC × ERC)^0.46
- Supports all 22 NFDRS fuel models (A-Z, no M)
- Configurable single model or spatially-varying model map

References:
    - Argonne (Yu/Feng): ERC/BI calculation code (primary reference)
    - Bradshaw et al. 1984: NFDRS technical documentation
    - firelab/NFDRS4-TechDoc: NFDRSV4Calc.py (validation)
    - NCAR/fire-indices: Corrected June 2024 (validation)
"""

import numpy as np

from aorc_tools.config import NFDRS_FUEL_MODELS, NFDRS_CTA, DEFAULT_FUEL_MODEL


def get_fuel_params(model_code=None):
    """Get fuel model parameters, converted to calculation units.

    Args:
        model_code: NFDRS fuel model letter (A-Z). Default from config.

    Returns:
        dict with all parameters. Loadings are in lbs/ft² (CTA-converted).
    """
    if model_code is None:
        model_code = DEFAULT_FUEL_MODEL

    fm = NFDRS_FUEL_MODELS[model_code].copy()

    # Convert loadings from tons/acre to lbs/ft²
    for key in ["L1", "L10", "L100", "L1000", "LWOOD", "LHERB"]:
        fm[f"w{key[1:].lower()}"] = fm[key] * NFDRS_CTA

    # Surface-area-to-volume ratios (already in 1/ft)
    fm["sg1d"] = fm["SG1"]
    fm["sg10d"] = fm["SG10"]
    fm["sg100d"] = fm["SG100"]
    fm["sg1000d"] = fm["SG1000"]
    fm["sgwood"] = fm["SGWOOD"]
    fm["sgherb"] = fm["SGHERB"]

    fm["depth"] = fm["DEPTH"]
    fm["mxd"] = fm["MXD"]
    fm["hd"] = fm["HD"]
    fm["wndfc"] = fm["WNDFC"]
    fm["hl"] = fm["HD"]  # Live heat = dead heat (standard assumption)

    return fm


def compute_erc_bi(fm1, fm10, fm100, fm1000, mcherb, mcwood, ws_mph,
                   fuel_model=None, slope_angle=12.67):
    """Compute ERC, SC, and BI from fuel moisture and wind speed.

    Ported directly from Argonne's code. Vectorized numpy implementation
    that operates on arrays (one value per spatial point per timestep).

    Args:
        fm1: 1-hr dead fuel moisture (%).
        fm10: 10-hr dead fuel moisture (%).
        fm100: 100-hr dead fuel moisture (%).
        fm1000: 1000-hr dead fuel moisture (%).
        mcherb: Live herbaceous fuel moisture (%).
        mcwood: Live woody fuel moisture (%).
        ws_mph: Wind speed in mph.
        fuel_model: NFDRS fuel model code (default from config).
        slope_angle: Terrain slope angle in degrees (default 12.67).

    Returns:
        dict with keys: SC, ERC, BI (all arrays matching input shape).
    """
    fm = get_fuel_params(fuel_model)

    # Ensure all inputs are float arrays
    fm1 = np.asarray(fm1, dtype=np.float64)
    fm10 = np.asarray(fm10, dtype=np.float64)
    fm100 = np.asarray(fm100, dtype=np.float64)
    fm1000 = np.asarray(fm1000, dtype=np.float64)
    mcherb = np.asarray(mcherb, dtype=np.float64)
    mcwood = np.asarray(mcwood, dtype=np.float64)
    ws_mph = np.asarray(ws_mph, dtype=np.float64)

    # Extract fuel model parameters
    w1d = fm["w1"]
    w10d = fm["w10"]
    w100d = fm["w100"]
    w1000d = fm["w1000"]
    wwood = fm["wwood"]
    wherb = fm["wherb"]
    sg1d = fm["sg1d"]
    sg10d = fm["sg10d"]
    sg100d = fm["sg100d"]
    sg1000d = fm["sg1000d"]
    sgwood = fm["sgwood"]
    sgherb = fm["sgherb"]
    hd = fm["hd"]
    hl = fm["hl"]
    mxd = fm["mxd"]
    depth = fm["depth"]
    wndfc = fm["wndfc"]

    # Physical constants
    stdl = 0.0555     # mineral content (same for dead and live)
    rhodl = 32.0      # particle density (lb/ft³, same for dead and live)
    sdl = 0.01        # effective mineral content
    etasdl = 0.174 * sdl ** (-0.19)

    # =========================================================================
    # Herbaceous curing and fuel loading adjustments (Argonne method)
    # =========================================================================
    fctcur = np.clip(1.33 - 0.0111 * mcherb, 0.0, 1.0)
    wherbc = fctcur * wherb        # cured herbaceous → dead
    wherbp = wherb - wherbc        # remaining live herbaceous
    w1dp = w1d + wherbc            # adjusted 1-hr dead loading

    wtotd = w1dp + w10d + w100d + w1000d   # total dead
    wtotl = wwood + wherbp                  # total live
    wtot = wtotd + wtotl

    # Avoid division by zero for models with no fuel
    wtot_safe = np.maximum(wtot, 1e-10)
    wtotd_safe = np.maximum(wtotd, 1e-10)
    wtotl_safe = np.maximum(wtotl, 1e-10)

    # =========================================================================
    # Net fuel loadings
    # =========================================================================
    w1n = w1dp * (1.0 - stdl)
    w10n = w10d * (1.0 - stdl)
    w100n = w100d * (1.0 - stdl)
    wherbn = wherbp * (1.0 - stdl)
    wwoodn = wwood * (1.0 - stdl)

    rhobed = (wtot - w1000d) / np.maximum(depth, 1e-10)
    rhobar = ((wtotl * rhodl) + (wtotd * rhodl)) / wtot_safe
    betbar = rhobed / np.maximum(rhobar, 1e-10)

    # =========================================================================
    # Heating numbers (for live fuel extinction moisture)
    # =========================================================================
    hnu1 = w1n * np.exp(-138.0 / np.maximum(sg1d, 1))
    hnu10 = w10n * np.exp(-138.0 / np.maximum(sg10d, 1))
    hnu100 = w100n * np.exp(-138.0 / np.maximum(sg100d, 1))
    hnherb = wherbn * np.exp(-500.0 / np.maximum(sgherb, 1))
    hnwood = wwoodn * np.exp(-500.0 / np.maximum(sgwood, 1))
    hsum = np.maximum(hnherb + hnwood, 1e-10)
    wrat = (hnu1 + hnu10 + hnu100) / hsum

    # =========================================================================
    # SPREAD COMPONENT (SC) — surface-area weighting (Argonne method)
    # =========================================================================

    # Surface areas
    sa1 = (w1dp / rhodl) * sg1d
    sa10 = (w10d / rhodl) * sg10d
    sa100 = (w100d / rhodl) * sg100d
    sherbc = (wherbp / rhodl) * np.maximum(sgherb, 1)
    sawood = (wwood / rhodl) * np.maximum(sgwood, 1)

    sadead = sa1 + sa10 + sa100
    salive = sawood + sherbc
    sadead_safe = np.maximum(sadead, 1e-10)
    salive_safe = np.maximum(salive, 1e-10)

    # Surface-area weighting factors
    fct1 = sa1 / sadead_safe
    fct10 = sa10 / sadead_safe
    fct100 = sa100 / sadead_safe
    fcherb = sherbc / salive_safe
    fcwood = sawood / salive_safe

    fcded = sadead / np.maximum(sadead + salive, 1e-10)
    fcliv = salive / np.maximum(sadead + salive, 1e-10)

    wdeadn = fct1 * w1n + fct10 * w10n + fct100 * w100n
    wliven = fcwood * wwoodn + fcherb * wherbn

    # Weighted SAV ratios
    sgbrd = fct1 * sg1d + fct10 * sg10d + fct100 * sg100d
    sgbrl = fcwood * sgwood + fcherb * sgherb
    sgbrt = sgbrd * fcded + sgbrl * fcliv
    sgbrt_safe = np.maximum(sgbrt, 1.0)

    # Optimum packing ratio and reaction velocity
    betop = 3.348 * sgbrt_safe ** (-0.8189)
    gmamx = sgbrt_safe ** 1.5 / (495.0 + 0.0594 * sgbrt_safe ** 1.5)
    ad = 133.0 * sgbrt_safe ** (-0.7913)
    ratio = betbar / np.maximum(betop, 1e-10)
    gmaop = gmamx * ratio ** ad * np.exp(ad * (1.0 - ratio))

    # Propagating flux ratio
    zeta = (np.exp((0.792 + 0.681 * sgbrt_safe ** 0.5) * (betbar + 0.1))
            / (192.0 + 0.2595 * sgbrt_safe))

    # Live fuel moisture extinction (Argonne method)
    mclfe_denom = np.maximum(hnu1 + hnu10 + hnu100, 1e-10)
    mclfe = (fm1 * hnu1 + fm10 * hnu10 + fm100 * hnu100) / mclfe_denom
    mxl = (2.9 * wrat * (1.0 - mclfe / mxd) - 0.226) * 100.0
    mxl = np.maximum(mxl, mxd)

    # Weighted moisture contents (SC path)
    wtmcd = fct1 * fm1 + fct10 * fm10 + fct100 * fm100
    wtmcl = fcherb * mcherb + fcwood * mcwood
    dedrt = wtmcd / np.maximum(mxd, 1e-10)
    livrt = wtmcl / np.maximum(mxl, 1e-10)

    # SC MOISTURE DAMPING — Anderson (1969) coefficients
    etamd = 1.0 - 2.59 * dedrt + 5.11 * dedrt ** 2 - 3.52 * dedrt ** 3
    etamd = np.clip(etamd, 0.0, 1.0)
    etaml = 1.0 - 2.59 * livrt + 5.11 * livrt ** 2 - 3.52 * livrt ** 3
    etaml = np.clip(etaml, 0.0, 1.0)

    # Wind effect coefficients
    c = 7.47 * np.exp(-0.133 * sgbrt_safe ** 0.55)
    e = 0.715 * np.exp(-3.59e-4 * sgbrt_safe)
    b = 0.02526 * sgbrt_safe ** 0.54
    ufact = c * (ratio) ** (-e)

    # Slope factor
    slpfct = 5.275 * np.tan(np.radians(slope_angle)) ** 2
    phislp = slpfct * betbar ** (-0.3)

    # Reaction intensity (SC path)
    ir = gmaop * (wdeadn * hd * etasdl * etamd + wliven * hl * etasdl * etaml)

    # Wind factor (Argonne method — threshold at 0.9*IR)
    phiwnd_input = ws_mph * 88.0 * wndfc
    phiwnd1 = ufact * (0.9 * ir) ** b     # when wind*88*wndfc >= 0.9*IR
    phiwnd2 = ufact * phiwnd_input ** b    # when wind*88*wndfc < 0.9*IR
    phiwnd = np.where(phiwnd_input >= 0.9 * ir, phiwnd1, phiwnd2)

    # Heat sink
    htsink = rhobed * (
        fcded * (
            fct1 * np.exp(-138.0 / np.maximum(sg1d, 1)) * (250.0 + 11.16 * fm1)
            + fct10 * np.exp(-138.0 / np.maximum(sg10d, 1)) * (250.0 + 11.16 * fm10)
            + fct100 * np.exp(-138.0 / np.maximum(sg100d, 1)) * (250.0 + 11.16 * fm100)
        )
        + fcliv * (
            fcherb * np.exp(-138.0 / np.maximum(sgherb, 1)) * (250.0 + 11.16 * mcherb)
            + fcwood * np.exp(-138.0 / np.maximum(sgwood, 1)) * (250.0 + 11.16 * mcwood)
        )
    )
    htsink_safe = np.maximum(htsink, 1e-10)

    # SPREAD COMPONENT
    sc = ir * zeta * (1.0 + phislp + phiwnd) / htsink_safe

    # =========================================================================
    # ENERGY RELEASE COMPONENT (ERC) — load weighting (Argonne method)
    # =========================================================================

    # ERC uses load-based weighting (different from SC's surface-area weighting)
    fct1e = w1dp / wtotd_safe
    fct10e = w10d / wtotd_safe
    fct100e = w100d / wtotd_safe
    fct1000e = w1000d / wtotd_safe
    fwoode = wwood / wtotl_safe
    fhrbce = wherbp / wtotl_safe

    fcdede = wtotd / wtot_safe
    fclive = wtotl / wtot_safe
    wdedne = wtotd * (1.0 - stdl)
    wlivne = wtotl * (1.0 - stdl)

    sgbrde = fct1e * sg1d + fct10e * sg10d + fct100e * sg100d + fct1000e * sg1000d
    sgbrle = fwoode * sgwood + fhrbce * sgherb
    sgbrte = sgbrde * fcdede + sgbrle * fclive
    sgbrte_safe = np.maximum(sgbrte, 1.0)

    betope = 3.348 * sgbrte_safe ** (-0.8189)
    gmamxe = sgbrte_safe ** 1.5 / (495.0 + 0.0594 * sgbrte_safe ** 1.5)
    ade = 133.0 * sgbrte_safe ** (-0.7913)
    ratioe = betbar / np.maximum(betope, 1e-10)
    gmapme = gmamxe * ratioe ** ade * np.exp(ade * (1.0 - ratioe))

    # ERC weighted moisture content
    wtfmde = fct1e * fm1 + fct10e * fm10 + fct100e * fm100 + fct1000e * fm1000
    wtfmle = fwoode * mcwood + fhrbce * mcherb
    dedrte = wtfmde / np.maximum(mxd, 1e-10)
    livrte = wtfmle / np.maximum(mxl, 1e-10)

    # ERC MOISTURE DAMPING — Albini (1976) coefficients
    # CRITICAL: Different from SC damping (Anderson 1969)
    etamde = 1.0 - 2.0 * dedrte + 1.5 * dedrte ** 2 - 0.5 * dedrte ** 3
    etamde = np.clip(etamde, 0.0, 1.0)
    etamle = 1.0 - 2.0 * livrte + 1.5 * livrte ** 2 - 0.5 * livrte ** 3
    etamle = np.clip(etamle, 0.0, 1.0)

    # ERC reaction intensity
    ire = gmapme * (fcdede * wdedne * hd * etasdl * etamde
                    + fclive * wlivne * hl * etasdl * etamle)

    # Residence time
    tau = 384.0 / sgbrt_safe

    # ENERGY RELEASE COMPONENT
    erc = np.round(0.04 * ire * tau)

    # =========================================================================
    # BURNING INDEX
    # =========================================================================
    bi = 3.01 * np.power(np.maximum(sc * erc, 0.0), 0.46)

    return {
        "SC": sc,
        "ERC": erc,
        "BI": bi,
    }
