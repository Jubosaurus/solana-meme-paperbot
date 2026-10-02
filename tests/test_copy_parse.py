"""Copy-Bot: Kauf, Verkauf und Ueberweisung aus der Transaktion des Traders erkennen (parse_trade)."""
import pytest

import copy_bot as cb
from helpers import buy_tx, sell_tx, transfer_tx, swap_tx, WALLET, MINT, MINT2


def test_kauf():
    t = cb.parse_trade(buy_tx(sol=0.5, tokens=1_000_000, fee=5000, prio=95_000), WALLET)
    assert t["kind"] == "KAUF" and t["mint"] == MINT
    assert t["sol"] == pytest.approx(0.5)
    assert t["tokens"] == pytest.approx(1_000_000)
    assert t["price_sol"] == pytest.approx(0.5 / 1_000_000)
    assert t["fee_base"] == pytest.approx(0.000005) and t["fee_prio"] == pytest.approx(0.000095)
    assert t["pre_raw"] == 0 and t["delta_raw"] == 1_000_000 * 10**6
    assert t["quote_asset"] == "SOL"


def test_kauf_mit_jito_tip_und_bot_gebuehr():
    t = cb.parse_trade(buy_tx(sol=1.0, jito=1_000_000, botfee=10_000_000), WALLET)
    assert t["kind"] == "KAUF"
    assert t["sol"] == pytest.approx(1.0)               # Tip und Bot-Gebuehr nicht im Kaufbetrag
    assert t["jito"] == pytest.approx(0.001)
    assert t["other"] == pytest.approx(0.01)


def test_teilverkauf():
    t = cb.parse_trade(sell_tx(sol=0.3, tokens=250_000, pre=1_000_000), WALLET)
    assert t["kind"] == "VERKAUF"
    assert t["sol"] == pytest.approx(0.3)
    assert t["tokens"] == pytest.approx(250_000)
    assert abs(t["delta_raw"]) / t["pre_raw"] == pytest.approx(0.25)


def test_kompletter_verkauf_konto_geschlossen():
    t = cb.parse_trade(sell_tx(sol=0.8, tokens=1_000_000, pre=1_000_000), WALLET)
    assert t["kind"] == "VERKAUF" and abs(t["delta_raw"]) == t["pre_raw"]


def test_ueberweisung():
    t = cb.parse_trade(transfer_tx(tokens=1_000_000, pre=1_000_000), WALLET)
    assert t["kind"] == "UEBERWEISUNG"
    assert t["price_sol"] is None


def test_kauf_gegen_usdc_wird_in_sol_umgerechnet():
    tx = swap_tx(pre=None, post=500_000 * 10**6, sol=0, usdc_pre=100 * 10**6, usdc_post=50 * 10**6)
    t = cb.parse_trade(tx, WALLET, sol_usd=100.0)
    assert t["kind"] == "KAUF" and t["quote_asset"] == "USDC"
    assert t["sol"] == pytest.approx(0.5)
    assert t["mint"] == MINT                            # USDC selbst ist nie der gehandelte Coin


def test_usdc_ohne_sol_kurs_ist_kein_trade():
    tx = swap_tx(pre=None, post=500_000 * 10**6, sol=0, usdc_pre=100 * 10**6, usdc_post=50 * 10**6)
    assert cb.parse_trade(tx, WALLET, sol_usd=None) is None


def test_temporaeres_wsol_konto_ist_keine_gebuehr():
    t = cb.parse_trade(buy_tx(sol=0.4, wsol_temp=400_000_000), WALLET)
    assert t["kind"] == "KAUF"
    assert t["other"] == 0
    assert t["sol"] == pytest.approx(0.4)


def test_dauerhaftes_wsol_konto_zaehlt_zum_tausch():
    tx = buy_tx(sol=0.4, wsol_pre=1_000_000_000, wsol_post=600_000_000)
    t = cb.parse_trade(tx, WALLET)
    assert t["kind"] == "KAUF" and t["sol"] == pytest.approx(0.4)


def test_airdrop_ohne_unterschrift_wird_ignoriert():
    assert cb.parse_trade(buy_tx(sol=0, signer=False), WALLET) is None


def test_token_erhalten_ohne_zahlung_ist_kein_kauf():
    assert cb.parse_trade(buy_tx(sol=0), WALLET) is None


def test_fehlgeschlagene_transaktion():
    assert cb.parse_trade(buy_tx(err={"InstructionError": [2, "Custom"]}), WALLET) is None
    assert cb.parse_trade(None, WALLET) is None


def test_fremde_wallet_nicht_in_der_transaktion():
    assert cb.parse_trade(buy_tx(), MINT2) is None


def test_mini_bewegung_ist_kein_handel():
    t = cb.parse_trade(buy_tx(sol=0.0005), WALLET)
    assert t is None                                    # unter 0,001 SOL: Token ohne nennenswerte Zahlung
