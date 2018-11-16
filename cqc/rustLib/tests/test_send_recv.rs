extern crate cqc;
extern crate rust_lib;

use cqc::hdr;
use rust_lib::Cqc;
use std::net::Ipv4Addr;

fn test_send() {
    // Initialise the host name, port number, remote host address,
    // remote host port number and application id
    let hostname = String::from("localhost");
    let portno: u16 = 8803;
    let remote_host: u32 = u32::from(Ipv4Addr::new(127, 0, 0, 1));
    let remote_port: u16 = 8804;
    let app_id: u16 = 10;

    // In this example, we will not check for errors.
    // Initialise a CQC service.
    let mut cqc = Cqc::new(app_id, &hostname, portno).unwrap();

    // Execute a simple CQC command to create a new qubit
    let request = cqc.builder.cmd_new(0, hdr::CmdOpt::empty());
    cqc.encode_and_send(&request).unwrap();

    // Get the qubit id
    let qubit = cqc.wait_until_newok().unwrap();

    // Non-blocking send qubit to the given remote host
    cqc.send(qubit, app_id, remote_host, remote_port).unwrap();
    cqc.wait_until_done(1).unwrap();
}

fn test_recv() {
    // Initialise the host name, port number and application id
    let hostname = String::from("localhost");
    let portno: u16 = 8804;
    let app_id: u16 = 10;

    // In this example, we will not check for errors.
    // Initialise a CQC service.
    let mut cqc = Cqc::new(app_id, &hostname, portno).unwrap();

    // Receive qubit from any source
    let qubit: u16 = cqc.recv().unwrap();
    println!("The qubit received is {:?}", qubit);
}

#[test]
fn test_send_recv() {
    test_send();
    test_recv();
}
