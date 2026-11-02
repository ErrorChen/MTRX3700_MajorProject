# grab_jtag.tcl -- the JTAG frame grab, the PC's side: take a snapshot, read it over the USB-Blaster, decode it.
#
# Run it on the computer the DE1-SoC's USB-Blaster is plugged into, after programming a design with the JTAG frame
# grab (rtl/debug/frame_snap.sv in rtl/top/perceptionDemoTop.sv), from the repository:
#
#     quartus_stp -t tools/tcl/grab_jtag.tcl                    a snapshot now, into a new folder grab_<date>_<time>
#     quartus_stp -t tools/tcl/grab_jtag.tcl mygrab             into the folder mygrab
#     quartus_stp -t tools/tcl/grab_jtag.tcl mygrab --held      no new snapshot: read the one already held (after KEY1)
#     quartus_stp -t tools/tcl/grab_jtag.tcl mygrab --hstart 152    anything after the folder that is not --held goes to
#                                                             tools/capture/grab.py (--mvfp, --hstart, --vstart)
#
# On Windows quartus_stp is C:\intelFPGA_lite\18.1\quartus\bin64\quartus_stp.exe (or wherever Quartus 18.1 is).
#
# What it does:
#   1. finds the USB-Blaster and the DE1-SoC's FPGA, the probes GCTL and the memory GRAB (rtl/debug/frame_snap.sv);
#   2. flips GCTL's request and waits for a complete camera frame with matching recognition results;
#   3. reads the memory GRAB: the header first, for how many words the snapshot takes, then all of them;
#   4. writes them, in address order, two bytes a word, to <folder>/dump.bin, the bytes as frame_snap.sv laid them out;
#   5. runs tools/capture/grab.py --file <folder>/dump.bin --out <folder>, which checks the CRC and writes frame.png,
#      frame.hex, scene.hex and results.json. Missing Python or decode/CRC failure exits nonzero.
# Everything it prints goes into <folder>/grab_jtag.log too, with how long the JTAG read took.

load_package insystem_source_probe
load_package insystem_memory_edit
load_package jtag

set HERE  [file dirname [file normalize [info script]]]
set TOOLS [file normalize [file join $HERE .. capture]]

# ---- the arguments ---------------------------------------------------------------------------------------------------
set OUT ""; set HELD 0; set GRAB_ARGS {}
set REQUESTED_CABLE ""; set REQUESTED_DEVICE ""; set PYTHON ""
for {set i 0} {$i < [llength $argv]} {incr i} {
    set a [lindex $argv $i]
    if {$a in {--cable --device --python}} {
        incr i
        if {$i >= [llength $argv]} { error "missing value for $a" }
        switch -- $a {
            --cable { set REQUESTED_CABLE [lindex $argv $i] }
            --device { set REQUESTED_DEVICE [lindex $argv $i] }
            --python { set PYTHON [lindex $argv $i] }
        }
    } elseif {$a eq "--held"} { set HELD 1 } \
    elseif {$OUT eq "" && ![string match "-*" $a] && [llength $GRAB_ARGS] == 0} { set OUT $a } \
    else { lappend GRAB_ARGS $a }
}
if {$OUT eq ""} { set OUT [clock format [clock seconds] -format "grab_%Y%m%d_%H%M%S"] }
file mkdir $OUT
set LOG [open [file join $OUT grab_jtag.log] a]
set T0  [clock milliseconds]
set BEFORE {}; set ACCEPTED {}; set READ_BEFORE {}; set READ_AFTER {}
set REQUEST_TOGGLE null; set ACCEPTED_AT null; set READ_STARTED null; set READ_FINISHED null
set TOTAL_WORDS null; set HW ""; set DEV ""
proc jsonString {value} {
    set escaped [string map [list "\\" "\\\\" "\"" "\\\"" "\n" "\\n" "\r" "\\r" "\t" "\\t"] $value]
    return [format {"%s"} $escaped]
}
proc probeJson {state} {
    if {$state eq ""} { return null }
    set parts {}
    foreach field {count ack busy ready mode source} {
        lappend parts [format {"%s":%d} $field [dict get $state $field]]
    }
    return "\{[join $parts ,]\}"
}
proc writeMetadata {verified reason} {
    set mode [expr {$::HELD ? "held" : "fresh"}]
    set fields [list {"schema":"echo7-snapshot-transaction-v1"} \
        "\"mode\":[jsonString $mode]" "\"verified\":$verified" \
        "\"reason\":[jsonString $reason]" \
        "\"target\":\{\"cable\":[jsonString $::HW],\"device\":[jsonString $::DEV]\}" \
        "\"requestBefore\":[probeJson $::BEFORE]" "\"requestedToggle\":$::REQUEST_TOGGLE" \
        "\"accepted\":[probeJson $::ACCEPTED]" "\"readBefore\":[probeJson $::READ_BEFORE]" \
        "\"readAfter\":[probeJson $::READ_AFTER]" "\"startedHostMs\":$::T0" \
        "\"acceptedHostMs\":$::ACCEPTED_AT" "\"readStartedHostMs\":$::READ_STARTED" \
        "\"readFinishedHostMs\":$::READ_FINISHED" "\"memoryWords\":$::TOTAL_WORDS"]
    set f [open [file join $::OUT snapshot_metadata.json] w]
    puts $f "\{[join $fields ,]\}"
    close $f
}
proc say {msg} {
    set line [format "%6.2f s  %s" [expr {([clock milliseconds] - $::T0) / 1000.0}] $msg]
    puts $line; puts $::LOG $line; flush stdout; flush $::LOG
}
proc give_up {msg} { say "ERROR: $msg"; writeMetadata false $msg; close $::LOG; exit 1 }

# ---- 1. the cable, the FPGA, the probes and the memory ----------------------------------------------------------------
set HW ""; set DEV ""; set MATCHES {}
if {[catch {get_hardware_names} hws]} { give_up "no JTAG cable ($hws): is the USB-Blaster's cable plugged into this computer?" }
foreach hw $hws {
    if {$REQUESTED_CABLE ne "" && $hw ne $REQUESTED_CABLE} { continue }
    if {[catch {get_device_names -hardware_name $hw} devs]} { continue }
    foreach dev $devs {
        if {$REQUESTED_DEVICE ne "" && $dev ne $REQUESTED_DEVICE} { continue }
        if {[string match "*5CSEMA5*" $dev] || [string match "*02D120DD*" $dev]} { lappend MATCHES [list $hw $dev] }
    }
}
if {[llength $MATCHES] != 1} { give_up "expected one selected DE1-SoC FPGA, found [llength $MATCHES]: pass exact --cable and --device; matches=$MATCHES" }
lassign [lindex $MATCHES 0] HW DEV
say "cable: $HW, device: $DEV"

set PROBES -1; set PROBE_MATCHES {}
if {[catch {get_insystem_source_probe_instance_info -hardware_name $HW -device_name $DEV} insts]} { set insts {} }
foreach inst $insts { if {[lindex $inst 3] eq "GCTL"} { lappend PROBE_MATCHES $inst } }
if {[llength $PROBE_MATCHES] == 1} { set PROBES [lindex [lindex $PROBE_MATCHES 0] 0] }
set MEM -1; set MEM_DEPTH 0; set MEMORY_MATCHES {}
if {[catch {get_editable_mem_instances -hardware_name $HW -device_name $DEV} mems]} { set mems {} }
foreach inst $mems { if {[lindex $inst 5] eq "GRAB"} { lappend MEMORY_MATCHES $inst } }
if {[llength $MEMORY_MATCHES] == 1} {
    set MEM [lindex [lindex $MEMORY_MATCHES 0] 0]
    set MEM_DEPTH [lindex [lindex $MEMORY_MATCHES 0] 1]
}
if {[llength $PROBE_MATCHES] > 1 || [llength $MEMORY_MATCHES] > 1} {
    give_up "ambiguous frame-grab instances: expected one GCTL and one GRAB, found [llength $PROBE_MATCHES] and [llength $MEMORY_MATCHES]"
}
if {$PROBES < 0 || $MEM < 0} {
    give_up "the FPGA has no JTAG frame grab (probes GCTL: [expr {$PROBES < 0 ? "missing" : "found"}], memory GRAB:\
             [expr {$MEM < 0 ? "missing" : "found"}]): program the design with rtl/debug/frame_snap.sv in it first"
}

# probe bits, most significant first: count[15:0], ack, busy, ready, MODE[1:0]
proc probe {} {
    set deadline [expr {[clock milliseconds] + 3000}]
    while 1 {                          ;# a probe that is changing can be read half old, half new: read until two agree
        set a [read_probe_data -instance_index $::PROBES]
        set b [read_probe_data -instance_index $::PROBES]
        if {$a eq $b} { break }
        if {[clock milliseconds] > $deadline} { give_up "GCTL never stabilised within 3 s" }
    }
    if {![regexp {^[01]{1,21}$} $a]} { give_up "invalid GCTL probe bits" }
    set s [string range "[string repeat 0 21]$a" end-20 end]
    set count 0; foreach c [split [string range $s 0 15] ""] { set count [expr {($count << 1) | $c}] }
    return [list count $count ack [string index $s 16] busy [string index $s 17] ready [string index $s 18] \
        mode [expr {2*[string index $s 19]+[string index $s 20]}]]
}
proc controlState {} {
    set source [read_source_data -instance_index $::PROBES]
    if {![regexp {^[01]$} $source]} { give_up "invalid GCTL source bit" }
    set state [probe]
    if {[read_source_data -instance_index $::PROBES] ne $source} {
        give_up "GCTL source changed during state read; another controller is active"
    }
    dict set state source $source
    return $state
}
proc sameSnapshot {expected actual} {
    foreach field {count ack busy ready mode source} {
        if {[dict get $expected $field] != [dict get $actual $field]} { return 0 }
    }
    return 1
}

# ---- 2. the snapshot ------------------------------------------------------------------------------------------------------
start_insystem_source_probe -hardware_name $HW -device_name $DEV
set p [controlState]
if {$HELD} {
    if {![dict get $p ready] || [dict get $p busy] || [dict get $p ack] != [dict get $p source]} {
        end_insystem_source_probe
        give_up "no whole snapshot is held (LEDR3 is off): press KEY1 first, or leave out --held"
    }
    set BEFORE $p
    say "reading the snapshot already held (number [dict get $p count] since the board was programmed)"
} else {
    # Finish any preceding request before toggling; never cancel a pending one.
    set idleDeadline [expr {[clock milliseconds]+3000}]
    while {[dict get $p busy] || [dict get $p ack] != [dict get $p source]} {
        if {[clock milliseconds]>$idleDeadline} { give_up "GCTL did not become idle before request" }
        after 5; set p [controlState]
    }
    set BEFORE $p
    set req [dict get $p source]
    set new [expr {$req eq "1" ? 0 : 1}]
    set REQUEST_TOGGLE $new
    set t [clock milliseconds]
    write_source_data -instance_index $PROBES -value $new
    while 1 {
        set q [controlState]
        if {[dict get $q source] != $new} { give_up "GCTL source changed after request" }
        if {[dict get $q count] != [dict get $p count] && ![dict get $q busy] && [dict get $q ready] && [dict get $q ack] == $new} { break }
        if {[clock milliseconds] - $t > 3000} {
            end_insystem_source_probe
            if {[dict get $q busy]} {
                give_up "no snapshot after 3 s: raw camera frame or matching recognition result did not complete; read status and check camera clock/frame activity"
            }
            give_up "no fresh complete snapshot after 3 s: request not accepted or matching-result timeout; read buildId/schema/status before retrying"
        }
        after 5
    }
    set p $q
    say "snapshot [dict get $p count] taken in [expr {[clock milliseconds] - $t}] ms"
}
set ACCEPTED $p
set ACCEPTED_AT [clock milliseconds]
end_insystem_source_probe

# ---- 3. and 4. read the memory, write dump.bin --------------------------------------------------------------------------
proc words {start n} {                  ;# n words from start, as hex in address order (quartus_stp gives the highest first)
    set hex [read_content_from_memory -instance_index $::MEM -start_address $start -word_count $n -content_in_hex -timeout 60000]
    set out ""
    for {set k [expr {$n - 1}]} {$k >= 0} {incr k -1} { append out [string range $hex [expr {4 * $k}] [expr {4 * $k + 3}]] }
    return $out
}
set t [clock milliseconds]
# Check the same completed snapshot immediately before and after the memory
# transaction. A physical trigger/other host must not replace it mid-transfer.
start_insystem_source_probe -hardware_name $HW -device_name $DEV
set READ_BEFORE [controlState]
end_insystem_source_probe
set READ_STARTED [clock milliseconds]
if {![sameSnapshot $ACCEPTED $READ_BEFORE]} { give_up "snapshot replaced before memory read" }
if {[catch {begin_memory_edit -hardware_name $HW -device_name $DEV} err]} { give_up "cannot open the memory for reading: $err" }
set head [words 0 7]
scan $head "%4x%4x%4x%4x%4x%4x%4x" m1 m2 version w h fmt n
if {$m1 != 0x4752 || $m2 != 0x4142} {
    end_memory_edit
    give_up "the memory does not start with 'GRAB': no snapshot in it (press KEY1, or run without --held)"
}
set pix [expr {$fmt == 2 ? $w * $h / 2 : $w * $h}]
set total [expr {7 + 2 * $n + $pix + 1}]
set TOTAL_WORDS $total
if {$total > $MEM_DEPTH} { end_memory_edit; give_up "the header says $total words, but the memory has only $MEM_DEPTH" }
set data ""
for {set s 0} {$s < $total} {incr s 16384} {
    append data [words $s [expr {min(16384, $total - $s)}]]
}
end_memory_edit
start_insystem_source_probe -hardware_name $HW -device_name $DEV
set READ_AFTER [controlState]
end_insystem_source_probe
set READ_FINISHED [clock milliseconds]
if {![sameSnapshot $READ_BEFORE $READ_AFTER]} { give_up "snapshot replaced during memory read" }
set dt [expr {[clock milliseconds] - $t}]
set f [open [file join $OUT dump.bin] wb]
puts -nonewline $f [binary format H* $data]
close $f
writeMetadata true "stable snapshot transaction; CRC and schema are checked separately"
say "read $total words ([expr {2 * $total}] bytes: $w x $h, format $fmt, $n result words) in $dt ms; wrote [file join $OUT dump.bin]"

# ---- 5. decode it with tools/capture/grab.py ------------------------------------------------------------------------------------------
set cmd [concat [list [file join $TOOLS grab.py] --file [file join $OUT dump.bin] --out $OUT] $GRAB_ARGS]
set candidates {python3 python {py -3}}
if {$PYTHON ne ""} { set candidates [list [list $PYTHON]] }
set selected ""
foreach py $candidates {
    # Probe only the interpreter. Once it runs, a decoder error is fatal rather
    # than a reason to try another Python and accidentally report success.
    if {![catch {exec {*}$py -c {import sys; print(sys.executable)} 2>@1} result]} {
        set selected $py; break
    }
}
if {$selected eq ""} { give_up "no working Python interpreter; use --python with an absolute executable path" }
if {[catch {exec {*}$selected {*}$cmd 2>@1} result opts]} {
    say $result
    give_up "grab.py failed; the snapshot has NOT passed decoding/CRC checks"
}
say $result
close $LOG
