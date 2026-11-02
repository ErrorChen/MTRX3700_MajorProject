// Optional SystemVerilog interface for team integration; flat ports use the same types.
interface perceptionLink(input logic CLOCK_50, input logic reset);
    import perception_pkg::*;
    logic [31:0] timeUs;
    logic interactionEnable, interactionPermit;
    targetRequest_t targetRequest;
    logic targetRequestValid, targetRequestReady;
    targetReport_t targetReport;
    logic targetReportValid, targetReportReady;
    userEvent_t userEvent;
    logic userEventValid, userEventReady;
    perceptionStatus_t status;
    modport perception(input CLOCK_50, reset, timeUs, interactionEnable, interactionPermit,
        targetRequest, targetRequestValid, targetReportReady, userEventReady,
        output targetRequestReady, targetReport, targetReportValid, userEvent, userEventValid, status);
    modport controller(input CLOCK_50, reset, timeUs, targetRequestReady,
        targetReport, targetReportValid, userEvent, userEventValid, status,
        output interactionEnable, interactionPermit, targetRequest, targetRequestValid,
        targetReportReady, userEventReady);
    modport monitor(input CLOCK_50, reset, timeUs, interactionEnable, interactionPermit,
        targetRequest, targetRequestValid, targetRequestReady, targetReport, targetReportValid,
        targetReportReady, userEvent, userEventValid, userEventReady, status);
endinterface
