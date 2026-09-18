from pathlib import Path

path = Path("src/nika/net_env/isp/sndlib/abilene/network.xml")
backup = path.with_suffix(".xml.backup")

if not backup.exists():
    backup.write_bytes(path.read_bytes())
    print(f"[OK] Backup created: {backup}")
else:
    print(f"[SKIP] Backup already exists: {backup}")

text = path.read_text(encoding="ISO-8859-1")

new_node = """   <node id="YUMAng">
    <coordinates>
     <x>-114.6244</x>
     <y>32.6927</y>
    </coordinates>
   </node>
"""

node_marker = """  </nodes>
  <links>"""

if 'node id="YUMAng"' not in text:
    if node_marker not in text:
        raise RuntimeError("Could not locate </nodes>/<links> insertion point.")
    text = text.replace(node_marker, new_node + node_marker, 1)
    print("[OK] Added YUMAng node.")
else:
    print("[SKIP] YUMAng node already exists.")

new_link = """   <link id="SNVAng_YUMAng">
    <source>YUMAng</source>
    <target>SNVAng</target>
    <preInstalledModule>
     <capacity>9920.0</capacity>
     <cost>0.0</cost>
    </preInstalledModule>
    <additionalModules>
     <addModule>
      <capacity>40000.0</capacity>
      <cost>500.0</cost>
     </addModule>
    </additionalModules>
   </link>
"""

link_marker = """  </links>
 </networkStructure>"""

if 'link id="SNVAng_YUMAng"' not in text:
    if link_marker not in text:
        raise RuntimeError("Could not locate </links>/</networkStructure> insertion point.")
    text = text.replace(link_marker, new_link + link_marker, 1)
    print("[OK] Added SNVAng_YUMAng link.")
else:
    print("[SKIP] SNVAng_YUMAng link already exists.")

path.write_text(text, encoding="ISO-8859-1")

node_count = text.count("<node id=")
link_count = text.count("<link id=")
print(f"[INFO] node_count={node_count}")
print(f"[INFO] link_count={link_count}")
print("[DONE] Expected extended Abilene size: 13 routers, 13 edge hosts after deployment.")
