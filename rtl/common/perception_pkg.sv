// Member B/C contract v2. All public fields are unsigned and sampled on CLOCK_50.
// Layout follows docs/MEMBER_C_INTERFACE.md, most significant field first.
package perception_pkg;
    localparam int unsigned PERCEPTION_CONTRACT_VERSION = 2;
    localparam logic [9:0] DEFAULT_ACTIVE_BAY_MASK = 10'h07e;
    localparam logic [3:0] INVALID_BAY_ID = 4'hf;
    typedef enum logic [1:0] {TARGET_CLEAR=2'd0, TARGET_SELECT=2'd1} targetOperation_t;
    typedef enum logic [1:0] {KIND_NONE=2'd0, KIND_CALIBRATION=2'd1, KIND_SPEECH=2'd2} interactionKind_t;
    typedef enum logic [3:0] {
        INTERACTION_IDLE=4'd0, INTERACTION_WAIT_PERMIT=4'd1, INTERACTION_CAL_COLLECT=4'd2,
        INTERACTION_CAL_VALIDATE=4'd3, INTERACTION_CAL_COMMIT=4'd4, INTERACTION_LISTEN=4'd5,
        INTERACTION_CLASSIFY=4'd6, INTERACTION_RESULT_QUEUE=4'd7, INTERACTION_REARM=4'd8,
        INTERACTION_SPEECH_ARMED=4'd9
    } interactionState_t;
    typedef enum logic [7:0] {
        REPORT_OK=8'd0, REPORT_NO_SELECTION=8'd1, REPORT_ACQUIRING=8'd2, REPORT_NOT_FOUND=8'd3,
        REPORT_DUPLICATE_ID=8'd4, REPORT_FRAME_BAD=8'd5, REPORT_CONFIG_CHANGED=8'd6,
        REPORT_REQUEST_CHANGED=8'd7, REPORT_PIPELINE_NOT_READY=8'd8,
        REPORT_INVALID_REQUEST=8'd9, REPORT_LOW_QUALITY=8'd10, REPORT_RESOURCE_DROP=8'd11
    } reportReason_t;
    typedef enum logic [3:0] {
        EVENT_NONE=4'd0, EVENT_SPEECH_BAY_REQUEST=4'd1, EVENT_CALIBRATION_DONE=4'd2,
        EVENT_CALIBRATION_FAILED=4'd3, EVENT_INPUT_REJECTED=4'd4,
        EVENT_INTERACTION_CANCELLED=4'd5, EVENT_INTERACTION_TIMEOUT=4'd6
    } eventType_t;
    typedef enum logic [7:0] {
        REASON_OK=8'd0, REASON_LOW_CONFIDENCE=8'd1, REASON_BAY_DISABLED=8'd2,
        REASON_NO_SPEECH=8'd3, REASON_AUDIO_UNAVAILABLE=8'd4, REASON_CAL_CARD_INVALID=8'd5,
        REASON_CAL_SAMPLES_INVALID=8'd6, REASON_PERMIT_REVOKED=8'd7,
        REASON_ENABLE_REVOKED=8'd8, REASON_WAIT_TIMEOUT=8'd9,
        REASON_CAPTURE_TIMEOUT=8'd10, REASON_INTERNAL_ERROR=8'd11
    } eventReason_t;
    localparam int FAULT_CAMERA_TRANSPORT=0, FAULT_CANDIDATE_OVERFLOW=1,
        FAULT_MASK_BUFFER_OVERRUN=2, FAULT_CONFIG_REJECTED=3,
        FAULT_AUDIO_CAPTURE=4, FAULT_REQUEST_INVALID=5, FAULT_INTERNAL_PROTOCOL=6;
    typedef struct packed {
        targetOperation_t operation;
        logic [15:0] requestTag;
        logic [3:0] bayId;
    } targetRequest_t;
    typedef struct packed {
        logic [15:0] requestTag;
        logic [15:0] frameId;
        logic [31:0] captureStartUs;
        logic [15:0] configVersion;
        logic [3:0] bayId;
        logic frameGood, observed, locked, ambiguous, targetSelected;
        logic [7:0] centreU;
        logic [8:0] centreV;
        logic [7:0] boxWidth;
        logic [8:0] boxHeight;
        logic [7:0] quality;
        reportReason_t reason;
    } targetReport_t;
    typedef struct packed {
        logic [15:0] eventId;
        eventType_t eventType;
        logic [3:0] bayId;
        logic [7:0] quality;
        logic [31:0] issuedAtUs;
        logic [15:0] configVersion;
        eventReason_t reason;
        logic [15:0] interactionId;
    } userEvent_t;
    typedef struct packed {
        logic interactionBusy;
        interactionKind_t kind;
        interactionState_t state;
        logic calibrated, audioReady, perceptionReady;
        logic [15:0] activeCfgVersion;
        logic [15:0] reportDropCount;
        logic eventOverflow;
        logic [15:0] faultFlags;
        logic [15:0] interactionId;
        logic speechArmed;
    } perceptionStatus_t;

    // Private completed-frame input to targetTracker. boundRequest MUST be latched
    // at camera SOF together with the timestamp, version and glyph-bank ownership.
    // matchCount counts only accepted BLUE digits matching boundRequest.bayId.
    typedef struct packed {
        targetRequest_t boundRequest;
        logic [15:0] frameId;
        logic [31:0] captureStartUs;
        logic [15:0] configVersion;
        logic frameGood, resourceDrop;
        logic [4:0] matchCount;
        logic [8:0] xMin, xMax;
        logic [7:0] yMin, yMax;
        logic [7:0] quality;
    } frameObservation_t;

    function automatic logic bayEnabled(input logic [3:0] bayId);
        bayEnabled = (bayId >= 1 && bayId <= 6);
    endfunction
    function automatic logic freshTime(input logic [31:0] nowUs,
            input logic [31:0] stampUs, input logic [31:0] maxAgeUs);
        logic [31:0] ageUs;
        begin
            ageUs = nowUs - stampUs;
            freshTime = !ageUs[31] && ageUs <= maxAgeUs;
        end
    endfunction
    function automatic logic newerSequence(input logic [15:0] nextId,
            input logic [15:0] previousId);
        logic [15:0] delta;
        begin
            delta = nextId - previousId;
            newerSequence = delta != 0 && !delta[15];
        end
    endfunction
endpackage
