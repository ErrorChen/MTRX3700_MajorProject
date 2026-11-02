// Two 320x240 banks holding white and colour-foreground bits (37.5 KiB total).
// The colour bit permits same-frame quadrilateral extraction for perspective.
// Ownership is controlled by
// perceptionCore: only WRITING may be written and only READING may be read.
// No reset of memory data; FREE/WRITING/READY/READING state invalidates old data.
// Read data has one synchronous clock of latency. No full RGB frame is added.
module glyphBanks (
    input logic clk, writeEnable, writeBank,
    input logic [16:0] writeAddress,
    input logic writeWhite,writeColour,
    input logic readBank,
    input logic [16:0] readAddress,
    output logic readWhite,readColour
);
    (* ramstyle="M10K, no_rw_check" *) logic [1:0] bank0 [0:76799];
    (* ramstyle="M10K, no_rw_check" *) logic [1:0] bank1 [0:76799];
    logic [1:0] read0,read1;
    logic readBankDelayed;
    always_ff @(posedge clk) begin
        if(writeEnable && !writeBank) bank0[writeAddress]<={writeColour,writeWhite};
        if(writeEnable && writeBank) bank1[writeAddress]<={writeColour,writeWhite};
        read0<=bank0[readAddress]; read1<=bank1[readAddress];
        readBankDelayed<=readBank;
    end
    assign {readColour,readWhite}=readBankDelayed?read1:read0;
endmodule
