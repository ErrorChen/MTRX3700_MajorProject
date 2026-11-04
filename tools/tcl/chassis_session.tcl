# One persistent session owns BCTL/CCTL. All transactions and heartbeats use it.
load_package jtag
load_package insystem_source_probe
set cable [lindex $argv 0]
set device [lindex $argv 1]
if {$cable eq "AUTO"} { set cable "" }
if {$device eq "AUTO"} { set device "" }
# Quartus 18.1 intercepts stdout and buffers even explicit Tcl flushes until
# script exit. A real file channel bypasses that interception; stdin remains
# the command pipe and the same STP process retains exclusive JTAG ownership.
set responseChannel stdout
if {[llength $argv] >= 3 && [lindex $argv 2] ne ""} {
    set responseChannel [open [lindex $argv 2] w]
    fconfigure $responseChannel -buffering line -translation lf -encoding utf-8
}
proc reply {message} {
    puts $::responseChannel $message
    flush $::responseChannel
}
if {$cable eq "" || $device eq ""} {
    set targets {}
    foreach hw [get_hardware_names] {
        foreach dev [get_device_names -hardware_name $hw] {
            if {[string match "*5CSEMA5*" $dev] || [string match "*02D120DD*" $dev]} {
                lappend targets [list $hw $dev]
            }
        }
    }
    if {[llength $targets] != 1} { error "need exactly one FPGA, or explicit --cable and --device" }
    lassign [lindex $targets 0] cable device
}
set instance -1
set bInstance -1
foreach inst [get_insystem_source_probe_instance_info -hardware_name $cable -device_name $device] {
    if {[lindex $inst 3] eq "CCTL"} {
        if {$instance >= 0} { error "multiple CCTL endpoints" }
        set instance [lindex $inst 0]
    }
    if {[lindex $inst 3] eq "BCTL"} { set bInstance [lindex $inst 0] }
}
if {$instance < 0} { error "CCTL absent: program the repaired integrated SOF" }
start_insystem_source_probe -hardware_name $cable -device_name $device
proc bits {value width} {
    set result ""
    for {set i [expr {$width-1}]} {$i >= 0} {incr i -1} { append result [expr {($value >> $i) & 1}] }
    return $result
}
proc number {binary} {
    set result 0
    foreach bit [split $binary ""] { set result [expr {($result << 1) | $bit}] }
    return $result
}
proc probe {} {
    set until [expr {[clock milliseconds]+1500}]
    while {[clock milliseconds] < $until} {
        set a [read_probe_data -instance_index $::instance]
        set b [read_probe_data -instance_index $::instance]
        if {$a eq $b} {
            set value [number $a]
            # The build field is now the actual E707 firmware identifier;
            # protocol compatibility remains the independent v1/16-word meta.
            if {($value >> 96) != 0x4343544c || (($value >> 64) & 0xffff0000) != 0xe7070000 ||
                (($value >> 48) & 0xffff) != 0x0110} { error "unsupported CCTL magic/version/schema/count" }
            return $value
        }
    }
    error "CCTL probe stability timeout"
}
proc command {opcode payload} {
    set previous [probe]
    set ack [expr {($previous >> 47) & 1}]
    set old [number [read_source_data -instance_index $::instance]]
    if {(($old >> 63) & 1) != $ack} { error "CCTL previous command pending" }
    set ::sourceWord [expr {(($ack ^ 1) << 63) | ($opcode << 56) | ($payload & 0xffffffff)}]
    write_source_data -instance_index $::instance -value [bits $::sourceWord 64]
    set until [expr {[clock milliseconds]+1500}]
    while {[clock milliseconds] < $until} {
        set value [probe]
        if {(($value >> 47) & 1) != $ack} {
            set errorCode [expr {($value >> 40) & 0x7f}]
            if {$errorCode != 0} { error "CCTL rejected opcode=$opcode error=$errorCode" }
            return [expr {$value & 0xffffffff}]
        }
        after 1
    }
    error "CCTL acknowledgement timeout (delivery unconfirmed)"
}
proc status {{maintainLease 0}} {
    if {$maintainLease} { command 8 0 }
    command 2 0
    set values {}
    for {set page 0} {$page < 16} {incr page} {
        if {$maintainLease} { command 8 0 }
        set ::sourceWord [expr {($::sourceWord & ~(0xff << 48)) | ($page << 48)}]
        write_source_data -instance_index $::instance -value [bits $::sourceWord 64]
        lappend values [expr {[probe] & 0xffffffff}]
    }
    return [join $values ","]
}
proc bprobe {} {
    if {$::bInstance < 0} { error "BCTL endpoint absent" }
    set until [expr {[clock milliseconds]+1500}]
    while {[clock milliseconds] < $until} {
        set a [read_probe_data -instance_index $::bInstance]
        set b [read_probe_data -instance_index $::bInstance]
        if {$a eq $b} {
            set value [number $a]
            if {($value >> 96) != 0x42444247 || (($value >> 48) & 0xffff) != 0x0803 ||
                (($value >> 32) & 255) != 96} { error "unsupported BCTL schema8/public3/count96" }
            return $value
        }
    }
    error "BCTL probe stability timeout"
}
proc bstatus {{maintainLease 0}} {
    set initial [bprobe]
    set ack [expr {($initial >> 47) & 1}]
    set old [number [read_source_data -instance_index $::bInstance]]
    if {(($old >> 31) & 1) != $ack} { error "BCTL previous command pending" }
    set source [expr {(($ack ^ 1) << 31) | (5 << 24)}]
    write_source_data -instance_index $::bInstance -value [bits $source 32]
    set until [expr {[clock milliseconds]+1500}]
    while {1} {
        set header [bprobe]
        if {(($header >> 47) & 1) != $ack} { break }
        if {[clock milliseconds] >= $until} { error "BCTL freeze acknowledgement timeout" }
        after 1
    }
    if {$header & (1 << 46)} { error "BCTL freeze rejected" }
    set values [list [expr {($header >> 64) & 0xffffffff}]]
    for {set page 0} {$page < 96} {incr page} {
        if {$maintainLease} { command 8 0 }
        write_source_data -instance_index $::bInstance -value [bits [expr {$source | ($page << 8)}] 32]
        set value [bprobe]
        if {($value >> 32) != ($header >> 32)} { error "BCTL frozen header changed" }
        lappend values [expr {$value & 0xffffffff}]
    }
    return [join $values ","]
}
fconfigure stdin -buffering line
fconfigure stdout -buffering line
reply "CCTL_READY\t$cable\t$device"
while {[gets stdin line] >= 0} {
    set fields [split $line "\t"]
    set serial [lindex $fields 0]
    if {![string is integer -strict $serial]} { break }
    if {[catch {
        switch -- [lindex $fields 1] {
            TX {
                if {[llength $fields] != 4} { error "TX needs opcode and payload" }
                set opcode [lindex $fields 2]; set payload [lindex $fields 3]
                if {![string is integer -strict $opcode] || $opcode < 1 || $opcode > 13 ||
                    ![string is wideinteger -strict $payload] || $payload < 0 || $payload > 0xffffffff} { error "invalid TX arguments" }
                set answer [command $opcode $payload]
            }
            STATUS { set answer [status] }
            STATUS_LEASE { set answer [status 1] }
            BSTATUS { set answer [bstatus] }
            BSTATUS_LEASE { set answer [bstatus 1] }
            QUIT { reply "CCTL_OK\t$serial\tBYE"; break }
            default { error "unsupported session operation" }
        }
    } failure]} {
        reply "CCTL_ERROR\t$serial\t[string map [list \n { } \r { } \t { }] $failure]"
    } else { reply "CCTL_OK\t$serial\t$answer" }
}
end_insystem_source_probe
if {$responseChannel ne "stdout"} { close $responseChannel }
