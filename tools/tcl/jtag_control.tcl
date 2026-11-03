# Explicit discovery and B interface stimulus. No inferred target or chain index.
load_package jtag
load_package insystem_source_probe
set operation [lindex $argv 0]
if {$operation eq "list"} {
    if {[catch {get_hardware_names} cables]} { puts "ECHO7_NO_HARDWARE\t$cables"; exit 0 }
    foreach cable $cables {
        foreach device [get_device_names -hardware_name $cable] {
            if {[string match "*5CSEMA5*" $device] || [string match "*02D120DD*" $device]} {
                if {![regexp {^@([0-9]+):} $device unused index]} { error "cannot parse FPGA chain index: $device" }
                puts "ECHO7_TARGET\t$cable\t$device\t$index"
            }
        }
    }
    exit 0
}
if {$operation ni {control calibration-check trial-stream} ||
    ($operation ne "trial-stream" && [llength $argv] != 4) ||
    ($operation eq "trial-stream" && [llength $argv] ni {4 5})} {
    error "usage: list | control/calibration-check cable device commandWord | trial-stream cable device trials ?deadlineSeconds?"
}
set cable [lindex $argv 1]
set device [lindex $argv 2]
set command [lindex $argv 3]
if {$operation eq "trial-stream"} {
    if {![string is integer -strict $command] || $command < 1 || $command > 3} {
        error "trial-stream requires 1..3 complete trials"
    }
    set trialDeadlineSeconds 300
    if {[llength $argv] == 5} { set trialDeadlineSeconds [lindex $argv 4] }
    if {![string is integer -strict $trialDeadlineSeconds] || $trialDeadlineSeconds < 1 || $trialDeadlineSeconds > 900} {
        error "trial-stream deadlineSeconds must be 1..900"
    }
}
if {$cable ni [get_hardware_names] || $device ni [get_device_names -hardware_name $cable]} { error "explicit target is not present" }
set instances {}
foreach inst [get_insystem_source_probe_instance_info -hardware_name $cable -device_name $device] {
    if {[lindex $inst 3] eq "BCTL"} { lappend instances [lindex $inst 0] }
}
if {[llength $instances] != 1} { error "expected exactly one BCTL instance, found [llength $instances]" }
set instance [lindex $instances 0]
start_insystem_source_probe -hardware_name $cable -device_name $device
proc binary32 {value} {
    set binary ""
    for {set bit 31} {$bit >= 0} {incr bit -1} { append binary [expr {($value >> $bit) & 1}] }
    return $binary
}
proc stableProbe {} {
    set deadline [expr {[clock milliseconds]+3000}]
    while {[clock milliseconds] < $deadline} {
        set a [read_probe_data -instance_index $::instance]
        set b [read_probe_data -instance_index $::instance]
        if {$a eq $b} { return [string range "[string repeat 0 128]$a" end-127 end] }
    }
    error "BCTL probe did not stabilise"
}
proc transact {command} {
    set old [read_source_data -instance_index $::instance]
    set old [string range "[string repeat 0 32]$old" end-31 end]
    set previous [stableProbe]
    set acknowledged [string index $previous 80]
    if {[string index $old 0] ne $acknowledged} { error "previous BCTL command is still pending; do not overwrite it" }
    set toggle [expr {$acknowledged eq "0" ? 1 : 0}]
    set value [expr {($toggle << 31) | ($command & 0x7fffffff)}]
    write_source_data -instance_index $::instance -value [binary32 $value]
    set deadline [expr {[clock milliseconds]+3000}]
    while {[clock milliseconds] < $deadline} {
        set probe [stableProbe]
        # meta bit15 is ackToggle; meta bit14 is command error.
        if {[string index $probe 80] eq "$toggle"} {
            set ::lastActionProbe $probe
            return $value
        }
        after 2
    }
    error "BCTL command acknowledgement timeout"
}
proc unsignedBinary {bits} {
    set value 0
    foreach bit [split $bits ""] { set value [expr {($value << 1) | $bit}] }
    return $value
}
proc schemaWordCount {schema} {
    if {$schema ni {1 2 3 4 5 6 7}} { error "unsupported BCTL schema" }
    return [expr {$schema == 6 ? 160 : 96}]
}
proc frozenWord {heldSource address} {
    write_source_data -instance_index $::instance -value [binary32 [expr {($heldSource & 0xffff00ff) | ($address << 8)}]]
    after 1
    return [unsignedBinary [string range [stableProbe] 96 127]]
}
# A complete bank is retained before publication. Address changes preserve the
# freeze toggle; every returned word must carry the identical 96-bit header.
# The classic control/calibration output below remains unchanged.
proc trialFrozenStatus {} {
    set heldSource [transact [expr {5 << 24}]]
    set header [string range [stableProbe] 0 95]
    set magic [unsignedBinary [string range $header 0 31]]
    set build [unsignedBinary [string range $header 32 63]]
    set meta [unsignedBinary [string range $header 64 95]]
    set schema [expr {$meta >> 24}]
    set wordCount [schemaWordCount $schema]
    if {$magic != 0x42444247 ||
        (($meta >> 16) & 255) != 2 || ($meta & 255) != $wordCount || ($meta & 0x4000)} {
        error "trial-stream unsupported or rejected BCTL frozen header"
    }
    set identity [list $magic $build $schema]
    if {[info exists ::trialIdentity] && $identity ne $::trialIdentity} {
        error "trial-stream board identity changed during session"
    }
    set ::trialIdentity $identity
    set words {}
    for {set address 0} {$address < $wordCount} {incr address} {
        write_source_data -instance_index $::instance -value [binary32 [expr {($heldSource & 0xffff00ff) | ($address << 8)}]]
        # This BCTL is 128 bits and its address logic runs on CLOCK_50.
        # stableProbe performs two current-probe captures; one full JTAG read
        # exceeds the five 50 MHz source/settle edges by over an order of
        # magnitude. If the first read sees the old word, the comparison retries.
        # Avoid Windows' ~15 ms timer quantum per word. This argument does not
        # apply to arbitrary slower probe domains; see the handover evidence.
        set value [stableProbe]
        if {[string range $value 0 95] ne $header} { error "BCTL header changed during frozen status read" }
        lappend words [unsignedBinary [string range $value 96 127]]
    }
    if {[lindex $words 0] != 0x45425031 || [lindex $words 1] != (($schema << 16) | 2) ||
        [lindex $words [expr {$wordCount-4}]] != $build} { error "trial-stream frozen payload/header identity mismatch" }
    return [list $header $words]
}
proc trialRecord {phase trial bay action} {
    set serial $::trialSerial
    incr ::trialSerial
    puts "ECHO7_TRIAL_BEGIN\t$serial\t$phase\t$trial\t$bay"
    if {$action != 0} {
        transact $action
        set meta [string range $::lastActionProbe 64 95]
        puts "ECHO7_TRIAL_ACTION\t$serial\t[expr {($action >> 24) & 15}]\t$meta"
        if {[string index $::lastActionProbe 81] eq "1"} { error "trial-stream action rejected" }
    }
    lassign [trialFrozenStatus] header words
    puts "ECHO7_TRIAL_HEADER\t$serial\t$header"
    for {set address 0} {$address < [llength $words]} {incr address} {
        puts "ECHO7_TRIAL_WORD\t$serial\t$address\t[binary32 [lindex $words $address]]"
    }
    puts "ECHO7_TRIAL_END\t$serial"
    flush stdout
    # Preserve the complete frozen record before rejecting raw/transition mode.
    # CLEAR is cleanup and must remain usable while perception is disabled.
    if {$phase ne "CLEAR" && ([lindex $words 1] >> 16) >= 5 &&
        ([lindex $words 7] & 0x00e00000)} {
        error "RAW_CAMERA_MODE: algorithm trial requires SW9 down and capture/display processing active"
    }
    return $words
}
proc streamTrials {trials deadlineSeconds} {
    set ::trialSerial 0
    unset -nocomplain ::trialIdentity
    set started [clock milliseconds]
    set deadline [expr {$started+1000*$deadlineSeconds}]
    set initialOk 0
    set statusRecords 0
    set lastFrame -1
    set code [catch {
        trialRecord INITIAL 0 0 0
        set initialOk 1
        for {set trial 1} {$trial <= $trials} {incr trial} {
            for {set bay 1} {$bay <= 6} {incr bay} {
                set selected [trialRecord SELECT $trial $bay [expr {(1 << 24) | $bay}]]
                set request [lindex $selected end-7]
                set tag [expr {($request >> 4) & 65535}]
                if {($request >> 20) != 1 || ($request & 15) != $bay} {
                    error "trial-stream SELECT was acknowledged but active request differs"
                }
                set collected 0
                while {$collected < 5} {
                    if {[clock milliseconds] >= $deadline || $statusRecords >= 4096} {
                        error "trial-stream timeout/bound: trial=$trial bay=$bay samples=$collected; partial records retained"
                    }
                    set words [trialRecord STATUS $trial $bay 0]
                    incr statusRecords
                    set frame [lindex $words 3]
                    if {$frame > 65535} { error "trial-stream native frame exceeds 16 bits" }
                    if {$lastFrame >= 0} {
                        set delta [expr {($frame-$lastFrame) & 65535}]
                        if {$delta == 0} { continue }
                        if {$delta >= 32768} { error "trial-stream native frame moved backwards" }
                    }
                    set lastFrame $frame
                    # Contract v2 targetReport is 139 bits, low word first.
                    # Only tag/bay/frame choose the denominator. Bad, unlocked,
                    # ambiguous and stale results still count and stay emitted.
                    set report 0
                    for {set word 0} {$word < 5} {incr word} {
                        set report [expr {$report | ([lindex $words [expr {13+$word}]] << (32*$word))}]
                    }
                    if {(($report >> 123) & 65535) == $tag &&
                        (($report >> 107) & 65535) == $frame && (($report >> 55) & 15) == $bay} {
                        incr collected
                    }
                }
            }
        }
    } message]
    # The source is already identified before any SELECT. Clear after success
    # or a failed trial; an error retains its original nonzero result even if
    # cleanup succeeds. No assertion of visual success is made by this script.
    if {$initialOk} {
        set clearCode [catch {trialRecord CLEAR 0 0 [expr {2 << 24}]} clearMessage]
        if {$clearCode && !$code} { set code $clearCode; set message $clearMessage }
    }
    if {$code} { error $message }
    puts "ECHO7_TRIAL_DONE\t$trials\t$statusRecords\t[expr {[clock milliseconds]-$started}]"
    flush stdout
}
if {$operation eq "trial-stream"} {
    set trialCode [catch {streamTrials $command $trialDeadlineSeconds} trialMessage]
    end_insystem_source_probe
    if {$trialCode} { error $trialMessage }
    exit 0
}
set actionRejected 0
if {$command != 0} {
    set before [stableProbe]
    set schema 0
    foreach bit [split [string range $before 64 71] ""] { set schema [expr {($schema << 1) | $bit}] }
    if {$schema ni {1 2 3 4 5 6 7}} { error "unsupported BCTL schema before action; no command issued" }
    set opcode [expr {($command >> 24) & 15}]
    if {$opcode in {3 4} && $schema < 3} {
        error "interaction arming requires BCTL schema3 action acceptance; rebuild/program current source"
    }
    transact $command
    puts "ECHO7_ACTION\t$opcode\t[string range $::lastActionProbe 64 95]"
    set actionRejected [expr {[string index $::lastActionProbe 81] eq "1"}]
}
if {$operation eq "calibration-check" && !$actionRejected} {
    # One session avoids host startup/status-transfer delays hiding the short
    # real eight-frame sampling interval. The second arm is sent only after
    # the production FSM has reported busy; no success/sample is injected.
    if {$command != (3 << 24)} { error "calibration-check requires calibration arm" }
    set testedBusy 0
    set deadline [expr {[clock milliseconds]+8000}]
    while {[clock milliseconds] < $deadline} {
        set source [transact [expr {5 << 24}]]
        set upper [frozenWord $source 12]
        set busy [expr {($upper >> 11) & 1}]
        set state [expr {($upper >> 5) & 15}]
        if {!$testedBusy && $busy} {
            set source [transact [expr {3 << 24}]]
            set meta [string range $::lastActionProbe 64 95]
            puts "ECHO7_BUSY_ACTION\t$meta"
            set value [unsignedBinary $meta]
            if {!(($value >> 14) & 1) || (($value >> 12) & 3) != 2} {
                error "busy arm did not return BUSY_OR_DISABLED (FSM may have completed before the action); inspect trace"
            }
            set testedBusy 1
        }
        set stamp [frozenWord $source 2]
        set frame [frozenWord $source 3]
        set config [frozenWord $source 6]
        set sample [frozenWord $source [expr {[schemaWordCount $schema]-7}]]
        puts "ECHO7_CAL_TRACE\t$stamp\t$frame\t$config\t$upper\t$sample"
        if {$testedBusy && !$busy && $state == 9} { break }
        after 10
    }
    if {!$testedBusy} { error "no real busy calibration interval observed; check real red1/permit and trace" }
    if {$busy || $state != 9} { error "real calibration trace did not return to idle armed state before timeout" }
}
# Opcode5 freezes a coherent schema-sized status bank. Changing the address never
# flips the request toggle and cannot create another action or another frame.
set heldSource [transact [expr {5 << 24}]]
set header [stableProbe]
set frozenMeta [unsignedBinary [string range $header 64 95]]
set wordCount [schemaWordCount [expr {$frozenMeta >> 24}]]
if {[unsignedBinary [string range $header 0 31]] != 0x42444247 ||
    (($frozenMeta >> 16) & 255) != 2 || ($frozenMeta & 255) != $wordCount} {
    error "unsupported BCTL frozen header magic/schema/contract/length"
}
puts "ECHO7_HEADER\t[string range $header 0 95]"
for {set address 0} {$address < $wordCount} {incr address} {
    set wordSource [expr {($heldSource & 0xffff00ff) | ($address << 8)}]
    write_source_data -instance_index $instance -value [binary32 $wordSource]
    after 1
    set value [stableProbe]
    if {[string range $value 0 95] ne [string range $header 0 95]} { error "BCTL header changed during frozen status read" }
    puts "ECHO7_WORD\t$address\t[string range $value 96 127]"
}
end_insystem_source_probe
if {$actionRejected} { exit 3 }
