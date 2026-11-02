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
if {$operation ne "control" || [llength $argv] != 4} { error "usage: list | control cable device commandWord" }
set cable [lindex $argv 1]
set device [lindex $argv 2]
set command [lindex $argv 3]
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
            if {[string index $probe 81] eq "1"} { error "BCTL rejected command $command" }
            return $value
        }
        after 2
    }
    error "BCTL command acknowledgement timeout"
}
if {$command != 0} { transact $command }
# Opcode5 freezes a coherent 96-word status bank. Changing the address never
# flips the request toggle and cannot create another action or another frame.
set heldSource [transact [expr {5 << 24}]]
set header [stableProbe]
puts "ECHO7_HEADER\t[string range $header 0 95]"
for {set address 0} {$address < 96} {incr address} {
    set wordSource [expr {($heldSource & 0xffff00ff) | ($address << 8)}]
    write_source_data -instance_index $instance -value [binary32 $wordSource]
    after 1
    set value [stableProbe]
    if {[string range $value 0 95] ne [string range $header 0 95]} { error "BCTL header changed during frozen status read" }
    puts "ECHO7_WORD\t$address\t[string range $value 96 127]"
}
end_insystem_source_probe
