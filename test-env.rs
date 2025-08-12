use std::env;

fn main() {
    println!("FLAVOR_LAUNCHER_CLI = {:?}", env::var("FLAVOR_LAUNCHER_CLI"));
    println!("Args: {:?}", env::args().collect::<Vec<_>>());
}