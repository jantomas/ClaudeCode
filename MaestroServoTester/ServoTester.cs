using Spectre.Console;

namespace MaestroServoTester;

/// <summary>
/// Interactive servo wiring test utility
/// </summary>
public class ServoTester
{
    private readonly MaestroController _controller;
    private readonly Dictionary<int, ServoInfo> _channelToServo;
    private readonly Dictionary<(int leg, string joint), int> _servoToChannel;

    private static readonly string[] LegNames = new[]
    {
        "Front Right",
        "Middle Right",
        "Rear Right",
        "Rear Left",
        "Middle Left",
        "Front Left"
    };

    public ServoTester(MaestroController controller, Dictionary<string, int> channelMapping)
    {
        _controller = controller;
        _channelToServo = new Dictionary<int, ServoInfo>();
        _servoToChannel = new Dictionary<(int, string), int>();

        BuildChannelMap(channelMapping);
    }

    private void BuildChannelMap(Dictionary<string, int> channelMapping)
    {
        foreach (var kvp in channelMapping)
        {
            var parts = kvp.Key.Split('.');
            if (parts.Length == 2 && int.TryParse(parts[0], out int legIdx))
            {
                string joint = parts[1];
                int channel = kvp.Value;

                var servoInfo = new ServoInfo(legIdx, joint, channel);
                _channelToServo[channel] = servoInfo;
                _servoToChannel[(legIdx, joint)] = channel;
            }
        }
    }

    public void PrintChannelMap()
    {
        var table = new Table()
            .Border(TableBorder.Rounded)
            .Title("[bold yellow]SERVO CHANNEL MAPPING[/]");

        table.AddColumn(new TableColumn("[bold]Channel[/]").Centered());
        table.AddColumn(new TableColumn("[bold]Leg[/]").Centered());
        table.AddColumn(new TableColumn("[bold]Joint[/]").Centered());
        table.AddColumn(new TableColumn("[bold]Description[/]"));

        for (int channel = 0; channel < 18; channel++)
        {
            if (_channelToServo.TryGetValue(channel, out var info))
            {
                string legName = info.LegIndex < LegNames.Length ? LegNames[info.LegIndex] : $"Leg {info.LegIndex}";
                string description = $"{legName} - {info.Joint.ToUpper()}";

                table.AddRow(
                    channel.ToString(),
                    info.LegIndex.ToString(),
                    info.Joint,
                    description
                );
            }
            else
            {
                table.AddRow(
                    channel.ToString(),
                    "[dim]N/A[/]",
                    "[dim]N/A[/]",
                    "[dim]Not configured[/]"
                );
            }
        }

        AnsiConsole.Write(table);
    }

    public void TestChannel(int channel, int durationMs = 2000)
    {
        if (!_channelToServo.TryGetValue(channel, out var info))
        {
            AnsiConsole.MarkupLine($"[red]✗ Channel {channel} is not configured in hardware.yaml[/]");
            return;
        }

        var panel = new Panel(
            new Markup($"""
                [bold yellow]Expected Movement:[/]
                  [cyan]Leg:[/]   {info.LegIndex} ([green]{GetLegName(info.LegIndex)}[/])
                  [cyan]Joint:[/] {info.Joint.ToUpper()}

                {GetJointDescription(info.Joint)}
                """))
            .Header($"[bold white on blue] TESTING CHANNEL {channel} [/]")
            .Border(BoxBorder.Double);

        AnsiConsole.Write(panel);
        AnsiConsole.WriteLine();

        // Test sequence: 90° → 60° → 120° → 90°
        var testSequence = new[]
        {
            (angle: 90, name: "Neutral (90°)"),
            (angle: 60, name: "Min (-30°)"),
            (angle: 120, name: "Max (+30°)"),
            (angle: 90, name: "Neutral (90°)")
        };

        int delayPerStep = durationMs / testSequence.Length;

        foreach (var (angle, name) in testSequence)
        {
            AnsiConsole.MarkupLine($"[yellow]→[/] Moving to [bold]{name}[/]...");
            _controller.SetAngle(channel, angle);
            Thread.Sleep(delayPerStep);
        }

        AnsiConsole.MarkupLine($"[green]✓ Channel {channel} test complete[/]");
        AnsiConsole.WriteLine();
    }

    public void TestLeg(int legIdx, int durationMs = 2000)
    {
        AnsiConsole.MarkupLine($"\n[bold yellow]═══ TESTING LEG {legIdx} - {GetLegName(legIdx)} ═══[/]\n");

        string[] joints = { "coxa", "femur", "tibia" };

        foreach (var joint in joints)
        {
            if (_servoToChannel.TryGetValue((legIdx, joint), out int channel))
            {
                TestChannel(channel, durationMs);
                Thread.Sleep(500);
            }
            else
            {
                AnsiConsole.MarkupLine($"[dim]⚠ Leg {legIdx} joint {joint} not configured[/]");
            }
        }

        AnsiConsole.MarkupLine($"[green]✓ Leg {legIdx} test complete[/]\n");
    }

    public void TestAllServos(int durationMs = 1500)
    {
        AnsiConsole.MarkupLine("\n[bold yellow]═══ TESTING ALL SERVOS SEQUENTIALLY ═══[/]");
        AnsiConsole.MarkupLine("Watch each servo move in sequence.\n");

        for (int channel = 0; channel < 18; channel++)
        {
            if (_channelToServo.ContainsKey(channel))
            {
                TestChannel(channel, durationMs);
                Thread.Sleep(500);
            }
        }

        // Return all to neutral
        AnsiConsole.MarkupLine("[cyan]Returning all servos to neutral position...[/]");
        MoveAllToNeutral();
        AnsiConsole.MarkupLine("[green]✓ All servos test complete[/]\n");
    }

    public void MoveAllToNeutral()
    {
        foreach (var channel in _channelToServo.Keys)
        {
            _controller.MoveToNeutral(channel);
        }
    }

    private string GetLegName(int legIdx)
    {
        return legIdx < LegNames.Length ? LegNames[legIdx] : $"Leg {legIdx}";
    }

    private string GetJointDescription(string joint)
    {
        return joint.ToLower() switch
        {
            "coxa" => "[dim]COXA: Hip joint - controls leg rotation (forward/backward)\n        Movement rotates leg horizontally around body attachment point.[/]",
            "femur" => "[dim]FEMUR: Upper leg joint - controls leg lift (up/down)\n         Movement raises or lowers the leg vertically.[/]",
            "tibia" => "[dim]TIBIA: Lower leg joint - controls foot extension\n         Movement extends or retracts the foot (shin joint).[/]",
            _ => ""
        };
    }
}
