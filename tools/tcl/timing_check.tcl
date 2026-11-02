# Post-fit timing gate, checked against local Quartus 18.1 Tcl help.
load_package sta
load_package report
if {[llength $argv] < 2 || [llength $argv] > 3 || ([llength $argv] == 3 && [lindex $argv 2] ne "--post-map-audit")} {
    error "usage: timing_check.tcl project output.json ?--post-map-audit?"
}
set project [lindex $argv 0]
set output [lindex $argv 1]
set postMap [expr {[llength $argv] == 3}]
project_open $project
if {$postMap} {create_timing_netlist -post_map} else {create_timing_netlist}
read_sdc
update_timing_netlist
set fail 0
set records {}
set skewRecords {}
set grayRecords {}
set payloadRecords {}
set netRecords {}
set clockNames {}
foreach_in_collection clock [get_clocks *] { lappend clockNames [get_clock_info $clock -name] }
foreach required {CLOCK_50 PCLK} {
    if {$required ni $clockNames} { set fail 1; post_message -type error "required clock absent: $required" }
}
# Evaluate every available analysis corner, not only the last fitter report.
foreach_in_collection corner [get_available_operating_conditions] {
    set_operating_conditions $corner
    update_timing_netlist
    set cornerName [get_operating_conditions_info $corner -model]
    if {$project eq "PartBDebug"} {
        foreach spec {{writeGray 9} {readGray 9} {timeGray 32}} {
            lassign $spec stem expected
            set fromRegs [get_registers [format {*cameraBridge*|%s[*]} $stem]]
            set toRegs [get_registers [format {*cameraBridge*|%sMeta[*]} $stem]]
            set sourceCount [get_collection_size $fromRegs]
            set destinationCount [get_collection_size $toRegs]
            set timedCount [get_collection_size [get_timing_paths -setup -from $fromRegs -to $toRegs -npaths 100]]
            set falseCount [get_collection_size [get_timing_paths -false_path -from $fromRegs -to $toRegs -npaths 100]]
            if {$sourceCount != $expected || $destinationCount != $expected || $timedCount != $expected || $falseCount != 0} {
                set fail 1
                post_message -type error "Gray CDC mapping mismatch $stem: expected=$expected source=$sourceCount destination=$destinationCount timed=$timedCount false=$falseCount"
            }
            lappend grayRecords "{\"corner\":\"$corner\",\"name\":\"$stem\",\"expected\":$expected,\"sourceCount\":$sourceCount,\"destinationCount\":$destinationCount,\"timedPathCount\":$timedCount,\"falsePathCount\":$falseCount}"
        }
    }
    if {$project eq "PartBDebug"} {
        # A held asynchronous mailbox has no same-edge hold relationship.
        # Prove that excluding that relationship did not cut its setup bound.
        foreach instance {resultToCamera *cameraBridge*|requestCdc} {
            set fromRegs [get_registers "${instance}|heldData\[*\]"]
            set toRegs [get_registers "${instance}|destinationData\[*\]"]
            set expected [get_collection_size $toRegs]
            set timed [get_collection_size [get_timing_paths -setup -from $fromRegs -to $toRegs -npaths 4096]]
            set cutSetup [get_collection_size [get_timing_paths -setup -false_path -from $fromRegs -to $toRegs -npaths 4096]]
            set hold [get_collection_size [get_timing_paths -hold -from $fromRegs -to $toRegs -npaths 4096]]
            if {$expected == 0 || $timed != $expected || $cutSetup != 0 || $hold != 0} {
                set fail 1
                post_message -type error "Payload CDC coverage failed $instance: expected=$expected setup=$timed cutSetup=$cutSetup hold=$hold"
            }
            lappend payloadRecords "{\"corner\":\"$corner\",\"instance\":\"$instance\",\"destinationCount\":$expected,\"setupPathCount\":$timed,\"cutSetupCount\":$cutSetup,\"sameEdgeHoldCount\":$hold}"
        }
        set netFile [file join [file dirname $output] "net_delay_$corner.txt"]
        report_net_delay -nworst 1 -file $netFile
        # Standard Edition writes a table but does not return the path/slack
        # pair returned by report_max_skew. Check both constraint summary rows.
        set netHandle [open $netFile r]
        set netText [read $netHandle]
        close $netHandle
        set rows [regexp -all -inline {;\s*set_net_delay\s*;\s*([-+0-9.]+)\s*;\s*([-+0-9.]+)\s*;\s*([-+0-9.]+)\s*;} $netText]
        set netCount 0
        set netSlack 1e9
        foreach {whole slack required actual} $rows {
            incr netCount
            if {$required != 20.0 || $slack < 0 || $actual > 20.0} {set fail 1}
            if {$slack < $netSlack} {set netSlack $slack}
        }
        if {$netCount != 2} {error "Expected two payload net bound summaries; found $netCount"}
        lappend netRecords "{\"corner\":\"$corner\",\"pathCount\":$netCount,\"worstSlackNs\":$netSlack}"
    }
    foreach check {setup hold recovery removal} {
        set worst null
        foreach_in_collection path [get_timing_paths -$check -npaths 1] {
            set slack [get_path_info $path -slack]
            set worst $slack
            if {$slack < 0} { set fail 1 }
        }
        lappend records "{\"corner\":\"$corner\",\"model\":\"$cornerName\",\"check\":\"$check\",\"worstSlackNs\":$worst}"
    }
    # Quartus 18.1 returns {number-of-paths worst-slack}; get_timing_paths
    # does not expose maximum-skew paths. Keep each real corner's full report.
    # Preserve actual chain identity; numerical MTBF is not this timing gate.
    set syncFile [file join [file dirname $output] "synchronisers_$corner.txt"]
    report_metastability -nchains 5000 -file $syncFile
    set skewFile [file join [file dirname $output] "max_skew_$corner.txt"]
    set skewResult [report_max_skew -file $skewFile -npaths 1 -detail full_path]
    set skewCount [lindex $skewResult 0]
    set skewSlack [lindex $skewResult 1]
    if {$skewCount > 0} {
        if {![string is double -strict $skewSlack]} { error "max-skew result is not numeric: $skewResult" }
        if {$skewSlack < 0} { set fail 1 }
    } else {
        set skewSlack null
        if {$project eq "PartBDebug"} { set fail 1; post_message -type error "B Gray CDC max-skew paths were not analysed" }
    }
    if {$project eq "PartBDebug" && $skewCount != 6} {
        set fail 1
        post_message -type error "Expected six earliest/latest reports for three Gray maximum-skew constraints; found $skewCount"
    }
    lappend skewRecords "{\"corner\":\"$corner\",\"pathCount\":$skewCount,\"worstSlackNs\":$skewSlack}"
}
set ucpFile [file join [file dirname $output] unconstrained.txt]
report_ucp -file $ucpFile
# The Python gate separately rejects nonzero unconstrained path counts.
set clocksJson {}
foreach name $clockNames { lappend clocksJson "\"[string map {\\ \\\\ \" \\\"} $name]\"" }
set f [open $output w]
puts $f "{\"schema\":\"echo7-timing-v2\",\"analysisStage\":\"[expr {$postMap ? "POST_MAP_CONSTRAINT_AUDIT" : "POST_FIT"}]\",\"status\":\"[expr {$fail ? "FAIL" : "PASS"}]\",\"clocks\":\[[join $clocksJson ,]\],\"checks\":\[[join $records ,]\],\"maxSkew\":\[[join $skewRecords ,]\],\"grayMappings\":\[[join $grayRecords ,]\],\"payloadMappings\":\[[join $payloadRecords ,]\],\"netDelay\":\[[join $netRecords ,]\]}"
close $f
delete_timing_netlist
project_close
if {$fail} { exit 1 }
