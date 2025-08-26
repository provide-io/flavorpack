use flavor::verify_package;
use std::path::Path;

fn main() {
    env_logger::init();

    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <package.pspf>", args[0]);
        std::process::exit(1);
    }

    let path = Path::new(&args[1]);
    match verify_package(path) {
        Ok(result) => {
            println!(
                "Package: {} v{}",
                result.package_name, result.package_version
            );
            println!("Format: {}", result.format);
            println!("Signature valid: {}", result.signature_valid);
            println!("Slots: {}", result.slot_count);
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }
}
