#!/usr/bin/env python3

from lxml import etree

# Test XML content based on your example
test_xml = '''<?xml version="1.0" encoding="utf-8" ?><!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv generator-info-name="IPTV">
	<channel id="CHANNEL ID 1">
		<display-name>CHANNEL DISPLAY NAME 1</display-name>
		<icon src="https://channel-icon-url-1.png" />
	</channel>
	<channel id="CHANNEL ID 2">
		<display-name>CHANNEL DISPLAY NAME 2</display-name>
		<icon src="https://channel-icon-url-2.png" />
	</channel>
		
	<programme start="20250702070000 +0000" stop="20250702110000 +0000" start_timestamp="1751439600" stop_timestamp="1751454000" channel="CHANNEL ID 1" >
		<title>CHANNEL DISPLAY NAME 1</title>
		<desc>CHANNEL DISPLAY NAME 1</desc>
	</programme>
	<programme start="20250702110000 +0000" stop="20250702150000 +0000" start_timestamp="1751454000" stop_timestamp="1751468400" channel="CHANNEL ID 2" >
		<title>CHANNEL DISPLAY NAME 2</title>
		<desc>CHANNEL DISPLAY NAME 2</desc>
	</programme>
</tv>'''

def test_iterparse_with_clear():
    print("=== Testing iterparse with elem.clear() ===")
    
    # Write test XML to a temp file
    with open('/tmp/test.xml', 'w') as f:
        f.write(test_xml)
    
    context = etree.iterparse('/tmp/test.xml', events=("end",))
    for event, elem in context:
        print(f"Processing: {elem.tag}")
        
        if elem.tag == "channel":
            print(f"  Channel ID: {elem.get('id')}")
            print(f"  Children before processing: {[child.tag for child in elem]}")
            
            # Try to find display-name
            display_name_elem = elem.find("display-name")
            if display_name_elem is not None:
                print(f"  Found display-name: '{display_name_elem.text}'")
            else:
                print(f"  ERROR: display-name not found!")
            
            # Try findtext
            display_name_text = elem.findtext("display-name")
            print(f"  findtext result: '{display_name_text}'")
            
        elif elem.tag == "programme":
            print(f"  Programme channel: {elem.get('channel')}")
            print(f"  Children before processing: {[child.tag for child in elem]}")
            
            # Try to find title
            title_elem = elem.find("title")
            if title_elem is not None:
                print(f"  Found title: '{title_elem.text}'")
            else:
                print(f"  ERROR: title not found!")
        
        # Clear element (this is what was causing the issue)
        elem.clear()
        print()

def test_iterparse_without_clear():
    print("=== Testing iterparse WITHOUT elem.clear() ===")
    
    context = etree.iterparse('/tmp/test.xml', events=("end",))
    for event, elem in context:
        print(f"Processing: {elem.tag}")
        
        if elem.tag == "channel":
            print(f"  Channel ID: {elem.get('id')}")
            print(f"  Children: {[child.tag for child in elem]}")
            
            # Try to find display-name
            display_name_elem = elem.find("display-name")
            if display_name_elem is not None:
                print(f"  Found display-name: '{display_name_elem.text}'")
            else:
                print(f"  ERROR: display-name not found!")
                
        elif elem.tag == "programme":
            print(f"  Programme channel: {elem.get('channel')}")
            print(f"  Children: {[child.tag for child in elem]}")
            
            # Try to find title
            title_elem = elem.find("title")
            if title_elem is not None:
                print(f"  Found title: '{title_elem.text}'")
            else:
                print(f"  ERROR: title not found!")
        
        print()

if __name__ == "__main__":
    test_iterparse_with_clear()
    test_iterparse_without_clear()
