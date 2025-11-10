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
    public string SerialPort { get; set; } = "COM3";
    public int BaudRate { get; set; } = 9600;
    public int DeviceNumber { get; set; } = 12;
}

public class SpecsConfig
{
    public int MinPulse { get; set; } = 992;
    public int MaxPulse { get; set; } = 8000;
    public int MinAngle { get; set; } = 0;
    public int MaxAngle { get; set; } = 180;
}

/// <summary>
/// Represents a servo configuration
/// </summary>
public record ServoInfo(int LegIndex, string Joint, int Channel);
