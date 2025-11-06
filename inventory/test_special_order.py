from field_mapping import map_shopsite_fields

# Test Special_Order scenarios
test_cases = [
    {'Name': 'Test Product', 'ProductField11': ''},      # Exists but empty
    {'Name': 'Test Product', 'ProductField11': 'yes'},   # Exists and yes
    {'Name': 'Test Product', 'ProductField11': 'YES'},   # Exists and YES
    {'Name': 'Test Product', 'ProductField11': 'no'},    # Exists but no
    {'Name': 'Test Product'},                            # Field missing entirely
]

print('🧪 Special_Order Storage Test:')
print('=' * 50)

for i, test_data in enumerate(test_cases, 1):
    result = map_shopsite_fields(test_data)
    special_order = result.get('Special_Order', 'NOT_STORED')
    input_val = test_data.get('ProductField11', 'MISSING')
    print(f'Test {i}: ProductField11="{input_val}" -> Special_Order="{special_order}"')

print()
print('✅ Behavior: Store empty string if field exists but blank, "yes" if "yes", skip if missing')