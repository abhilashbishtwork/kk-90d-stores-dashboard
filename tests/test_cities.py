from build.cities import city_for, display_name_for


def test_pune_prefix():
    assert city_for("PNQ KK Elpro Mall") == "Pune"


def test_delhi_prefix_is_ncr():
    assert city_for("DEL KK Omaxe Chandni Chowk") == "NCR"


def test_gurgaon_prefix_is_ncr():
    assert city_for("GGN KK Elan Miracle") == "NCR"


def test_ghaziabad_prefix_is_ncr():
    assert city_for("GZB KK Gaur City Online") == "NCR"


def test_faridabad_prefix_is_ncr():
    assert city_for("FDB KK Sector 31 Online") == "NCR"


def test_noida_word_prefix_is_ncr():
    assert city_for("Noida KK DLF Mall of India Online") == "NCR"


def test_greater_noida_prefix_is_ncr():
    assert city_for("Greater Noida KK Alpha 2 Online") == "NCR"


def test_noi_code_prefix_is_ncr():
    assert city_for("NOI KK Noida 141 Online") == "NCR"


def test_bengaluru_prefix():
    assert city_for("BLR KK SB Sarjapura") == "Bengaluru"


def test_chennai_prefix():
    assert city_for("MAA KK Mogappair") == "Chennai"


def test_hyderabad_prefix():
    assert city_for("HYD KK Manikonda Online") == "Hyderabad"


def test_jaipur_prefix():
    assert city_for("JAI KK Crystal Palm Mall Online") == "Jaipur"


def test_chandigarh_tricity_prefix():
    assert city_for("IXC KK Mohali Walk Pos") == "Chandigarh Tricity"


def test_unknown_prefix_is_unclassified():
    assert city_for("Some Unknown Store") == "Unclassified"


def test_prefix_match_is_case_insensitive():
    assert city_for("pnq kk elpro mall") == "Pune"


def test_display_name_strips_city_prefix_and_kk():
    assert display_name_for("PNQ KK Ravet") == "Ravet"


def test_display_name_strips_rename_suffix_noise():
    assert display_name_for("IXC KK CP 67 Mall - Kripsy Kreme - NCR") == "CP 67 Mall"


def test_display_name_handles_multi_word_prefix():
    assert display_name_for("Greater Noida KK Alpha 2 Online") == "Alpha 2"
