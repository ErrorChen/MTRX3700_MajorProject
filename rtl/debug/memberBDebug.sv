// Versioned B-only JTAG interface. The host writes a complete source word and
// holds its command/toggle until probe acknowledgement. snapshot_probes supplies
// metastability filtering; the additional whole-word stability check and held
// command/acknowledgement transaction provide a coherent payload boundary.
// A source address change with the same toggle selects another frozen word.
module memberBDebug #(
    parameter logic [31:0] BUILD_ID = 32'd0
) (
    input logic clk, reset,
    input logic [3071:0] debugWords,
    output logic commandValid,
    input logic commandReady,
    output logic commandClear,
    output logic [3:0] commandBayId,
    output logic calibrateArm, speechArm,
    output logic [1:0] orientationProfile,
    output logic autoCycle
);
    logic [31:0] sourceWord, previousSource, stableSource;
    logic [1:0] stableCount;
    logic ackToggle, pendingToggle, commandError,haveBaseline;
    logic [3071:0] frozenWords;
    logic [31:0] selectedWord, metaWord;
    logic [127:0] probeWord;
    snapshot_probes #(.ID("BCTL"),.SW(32),.PW(128)) probes (
        .clk(clk),.source(sourceWord),.probe(probeWord));

    always_comb begin
        selectedWord=32'd0;
        if(stableSource[15:8]<8'd96)
            selectedWord=frozenWords[stableSource[15:8]*32+:32];
        metaWord={8'd2,8'd2,ackToggle,commandError,6'd0,8'd96};
        probeWord={32'h42444247,BUILD_ID,metaWord,selectedWord};
    end

    always_ff @(posedge clk) begin
        if(reset) begin
            previousSource<=0;stableSource<=0;stableCount<=0;
            ackToggle<=0;pendingToggle<=0;commandError<=0;frozenWords<=0;haveBaseline<=0;
            commandValid<=0;commandClear<=0;commandBayId<=0;
            calibrateArm<=0;speechArm<=0;orientationProfile<=0;autoCycle<=0;
        end else begin
            calibrateArm<=0;speechArm<=0;
            if(commandValid && commandReady) begin
                commandValid<=0;
                ackToggle<=pendingToggle;
            end
            if(sourceWord!=previousSource) begin
                previousSource<=sourceWord;
                stableCount<=1;
            end else begin
                if(stableCount<3) stableCount<=stableCount+2'd1;
                // Three successive equal complete words are required. The host
                // must not issue another toggle while the command remains busy.
                if(stableCount>=2) begin
                    stableSource<=sourceWord;
                    // After KEY/reset, consume the stable pre-existing JTAG
                    // source as the baseline so an old SELECT cannot replay.
                    // The host reads acknowledgement before issuing a command.
                    if(!haveBaseline) begin
                        haveBaseline<=1;ackToggle<=sourceWord[31];
                    end else if(!commandValid && sourceWord[31]!=ackToggle) begin
                        pendingToggle<=sourceWord[31];
                        commandError<=0;
                        case(sourceWord[27:24])
                            4'd1: if(sourceWord[3:0]>=1 && sourceWord[3:0]<=6) begin
                                commandValid<=1;commandClear<=0;commandBayId<=sourceWord[3:0];
                            end else begin commandError<=1;ackToggle<=sourceWord[31];end
                            4'd2: begin commandValid<=1;commandClear<=1;commandBayId<=0;end
                            4'd3: begin calibrateArm<=1;ackToggle<=sourceWord[31];end
                            4'd4: begin speechArm<=1;ackToggle<=sourceWord[31];end
                            4'd5: begin frozenWords<=debugWords;ackToggle<=sourceWord[31];end
                            4'd6: begin orientationProfile<=sourceWord[1:0];ackToggle<=sourceWord[31];end
                            4'd7: begin autoCycle<=sourceWord[0];ackToggle<=sourceWord[31];end
                            default: begin commandError<=1;ackToggle<=sourceWord[31];end
                        endcase
                    end
                end
            end
        end
    end
endmodule
