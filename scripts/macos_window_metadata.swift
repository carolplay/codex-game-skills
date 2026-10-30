import Foundation
import AppKit
import CoreGraphics
// Read-only metadata only. Does not capture pixels, request permissions or send input.
// Save output under Git-ignored local-data; it includes the selected app path.
guard CommandLine.arguments.count == 2 else { fputs("Usage: window-metadata BUNDLE_ID\n",stderr);exit(2) }
let bundle=CommandLine.arguments[1]
let apps=NSWorkspace.shared.runningApplications.filter { $0.bundleIdentifier == bundle }
let pids=Set(apps.map {Int($0.processIdentifier)})
var d:[String:Any]=["read_only":true,"captured":ISO8601DateFormatter().string(from:Date()),"targetApps":apps.map {["pid":Int($0.processIdentifier),"path":$0.bundleURL?.path ?? "","active":$0.isActive,"hidden":$0.isHidden,"terminated":$0.isTerminated] as [String:Any]}]
func windows(_ option:CGWindowListOption)->Any {
 guard let a=CGWindowListCopyWindowInfo(option,kCGNullWindowID) as? [[String:Any]] else{return NSNull()}
 return a.filter {pids.contains(($0[kCGWindowOwnerPID as String] as? Int) ?? -1)}.map {w in Dictionary(uniqueKeysWithValues:["kCGWindowNumber","kCGWindowOwnerPID","kCGWindowBounds","kCGWindowIsOnscreen","kCGWindowLayer"].compactMap {k in w[k].map{(k,$0)}})}
}
d["targetWindowsAll"]=windows(.optionAll);d["targetWindowsOnScreen"]=windows(.optionOnScreenOnly)
if let session=CGSessionCopyCurrentDictionary() as? [String:Any] {d["session"]=session.filter { ["kCGSSessionOnConsoleKey","CGSSessionScreenIsLocked","kCGSessionLoginDoneKey"].contains($0.key)}} else {d["session"]=NSNull()}
var ids=[CGDirectDisplayID](repeating:0,count:16);var n:UInt32=0;let e=CGGetActiveDisplayList(16,&ids,&n)
d["activeDisplayQueryError"]=e.rawValue;d["displays"]=ids.prefix(Int(n)).map {id -> [String:Any] in let b=CGDisplayBounds(id);return ["id":id,"main":CGDisplayIsMain(id),"bounds":["x":b.origin.x,"y":b.origin.y,"w":b.width,"h":b.height],"pixelWidth":CGDisplayPixelsWide(id),"pixelHeight":CGDisplayPixelsHigh(id)]}
let data=try JSONSerialization.data(withJSONObject:d,options:[.prettyPrinted,.sortedKeys]);print(String(data:data,encoding:.utf8)!)
