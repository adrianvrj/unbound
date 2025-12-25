from starknet_py.hash.selector import get_selector_from_name

def print_selector(name):
    print(f"{name}: {hex(get_selector_from_name(name))}")

print_selector("get_total_usdc_deposited")
print_selector("total_supply")
print_selector("totalSupply")
print_selector("total_assets")
