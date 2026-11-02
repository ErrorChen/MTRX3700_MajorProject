# Requires CLOCK_50 and PCLK in the same set_clock_groups group so Quartus
# 18.1 Standard does not silently discard the Gray maximum-skew constraints.
# They remain asynchronous hardware domains. Every actual path between them
# is either physically bounded below or one of five single-bit first stages.
foreach spec {
 {writeGray 9}
 {readGray 9}
 {timeGray 32}
} {
 set stem [lindex $spec 0]
 set count [lindex $spec 1]
 set fromRegs [get_registers [format {*cameraBridge*|%s[*]} $stem]]
 set toRegs [get_registers [format {*cameraBridge*|%sMeta[*]} $stem]]
 if {[get_collection_size $fromRegs] != $count || [get_collection_size $toRegs] != $count} {
  error "Expected $count launch/first-stage Gray registers for $stem"
 }
 set_max_skew -from $fromRegs -to $toRegs 20.000
 set_max_delay -from $fromRegs -to $toRegs 20.000
 set_min_delay -from $fromRegs -to $toRegs 0.000
}

# Bundled payload is held until the destination acknowledges it. Bound its
# propagation below one destination clock, before the synchronised request can
# cause capture; do not mark the entire data bus as an unbounded false path.
foreach instance {resultToCamera *cameraBridge*|requestCdc} {
 set payloadFrom [get_registers "${instance}|heldData\[*\]"]
 set payloadTo [get_registers "${instance}|destinationData\[*\]"]
 if {[get_collection_size $payloadFrom] == 0 || [get_collection_size $payloadTo] == 0} {
  error "Missing bundled payload for $instance"
 }
 set_max_delay -from $payloadFrom -to $payloadTo 20.000
 set_min_delay -from $payloadFrom -to $payloadTo 0.000
 set_false_path -from [get_registers "${instance}|requestToggle"] -to [get_registers "${instance}|requestSync\[0\]"]
 set_false_path -from [get_registers "${instance}|acknowledgeToggle"] -to [get_registers "${instance}|acknowledgeSync\[0\]"]
}
set_false_path -from [get_registers {*cameraBridge*|sourceFault}] -to [get_registers {*cameraBridge*|faultSync[0]}]

# Only Intel's three serial TAP boundary ports are excluded from user I/O STA.
if {[get_collection_size [get_ports -nowarn {altera_reserved_tdi altera_reserved_tms}]] > 0} {
 set_false_path -from [get_ports {altera_reserved_tdi altera_reserved_tms}]
}
if {[get_collection_size [get_ports -nowarn {altera_reserved_tdo}]] > 0} {
 set_false_path -to [get_ports {altera_reserved_tdo}]
}
