# User scenarios on the retained NIKA reference

1. External clients cannot open web0.pod0, but the server reaches its local
   Leaf gateway and pod2 HTTP works. Diagnose all four incorrect peer ASes on
   leaf_router_0_1; restore each original Spine AS (65100–65103).
2. web0.pod1 resolves correctly, yet remote HTTP fails while the Leaf's four
   BGP sessions stay Established. Identify the outbound rejection of its
   10.1.1.0/24 service prefix and restore advertisements.
3. After DHCP renewal, client_0 cannot access remote services but its local
   gateway responds. Another external client works. Correct the DHCP router
   option and renew the actual lease; do not treat a client route patch as a
   durable server-side repair.
4. The application frontend returns503 while each of the original three pod0
   backends returns200 directly. DNS is healthy. Restore HAProxy backend
   port80 and verify both frontend and direct access.

Exact prompts, injections, Ground Truth, expected symptoms, controls and fixes
are in `dataset/nika92_Q/custom/`. Cases target actual reference devices and
peer/address values in `address-plan.json`; no old prototype names are used.
