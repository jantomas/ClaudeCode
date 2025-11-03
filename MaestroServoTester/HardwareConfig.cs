namespace MaestroServoTester;

/// <summary>
/// Hardware configuration models matching hardware.yaml structure
/// </summary>
public class HardwareConfig
{
    public ServosConfig Servos { get; set; } = new();
}

public class ServosConfig
{
    public DriverConfig Driver { get; set; } = new();
    public SpecsConfig Specs { get; set; } = new();
    public Dictionary<string, int> Channels { get; set; } = new();
    public Dictionary<string, int> Offsets { get; set; } = new();
}

public class DriverConfig
{
    public string Type { get; set; } = "PololuMaestro";
    public string Model { get; set; } = "Mini18";
    public string Serial_Port { get; set; } = "COM3";
    public int Baud_Rate { get; set; } = 115200;
    public int Device_Number { get; set; } = 12;
}

public class SpecsConfig
{
    public int Min_Pulse { get; set; } = 992;
    public int Max_Pulse { get; set; } = 8000;
    public int Min_Angle { get; set; } = 0;
    public int Max_Angle { get; set; } = 180;
}

/// <summary>
/// Represents a servo configuration
/// </summary>
public record ServoInfo(int LegIndex, string Joint, int Channel);
